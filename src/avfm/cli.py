"""Command-line interface for the active-vision face monitoring scaffold."""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2

from avfm import __version__
from avfm.actuation.factory import create_actuator
from avfm.app.pipeline import Pipeline
from avfm.app.recorder import NullRecorder, SessionRecorder
from avfm.app.replay import replay_session
from avfm.app.runner import Runner
from avfm.app.simulation import Scenario, run_simulation
from avfm.capabilities import collect_capabilities
from avfm.capture.factory import create_source
from avfm.config import AppConfig, load_config
from avfm.detection.factory import (
    create_detector,
    create_detectors,
    mediapipe_available,
    model_ready,
)
from avfm.errors import AvfmError, DependencyMissingError
from avfm.fatigue.calibration import EarCalibration
from avfm.logging import setup_logging
from avfm.metrics import CameraModel, compute_ear, compute_face_metrics
from avfm.models import MEDIAPIPE, YUNET, download_all, model_root, resolve_model_path, verify_all
from avfm.types import RunReport

logger = logging.getLogger("avfm.cli")


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=None, help="Explicit TOML config file")
    common.add_argument("--profile", default=None, help="Profile name from configs/<name>.toml")
    common.add_argument("--log-level", default=None, help="DEBUG|INFO|WARNING|ERROR")
    common.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    common.add_argument("--model-dir", default=None, help="Override the model root directory")

    parser = argparse.ArgumentParser(
        prog="avfm",
        description="Active Vision Face Monitoring scaffold: face tracking + fatigue monitoring.",
    )
    parser.add_argument("--version", action="version", version=f"avfm {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", parents=[common], help="Run the live pipeline")
    run.add_argument("--source", default=None, help="picamera | webcam:N | video:path | image:path")
    run.add_argument("--detector", choices=["auto", "yunet", "mediapipe"], default=None)
    run.add_argument("--detector-mode", choices=["single", "split"], default=None)
    run.add_argument("--tracking-backend", choices=["auto", "yunet", "mediapipe"], default=None)
    run.add_argument("--fatigue-backend", choices=["auto", "mediapipe", "none"], default=None)
    run.add_argument(
        "--detect-interval", type=int, default=None, help="Single-detector interval (frames)"
    )
    run.add_argument("--tracking-interval", type=int, default=None)
    run.add_argument("--fatigue-interval", type=int, default=None)
    run.add_argument("--servo", choices=["none", "mock", "pca9685", "auto"], default=None)
    run.add_argument("--flip", choices=["none", "horizontal", "vertical", "both"], default=None)
    run.add_argument("--fps", type=float, default=None)
    run.add_argument("--width", type=int, default=None)
    run.add_argument("--height", type=int, default=None)
    run.add_argument("--duration", type=float, default=None)
    run.add_argument("--max-frames", type=int, default=None)
    run.add_argument("--show", dest="show", action="store_true", default=None)
    run.add_argument("--no-show", dest="show", action="store_false")
    run.add_argument("--realtime", action="store_true", help="Pace video files in real time")
    run.add_argument("--record-dir", default=None)
    run.add_argument("--record-video", action="store_true")
    run.add_argument("--report-json", default=None)
    run.add_argument("--calibration-file", default=None)
    run.add_argument("--no-fatigue", action="store_true")
    run.add_argument("--dry-run", action="store_true", help="Print resolved config and exit")

    simulate = sub.add_parser(
        "simulate", parents=[common], help="Run the software-in-the-loop plant"
    )
    simulate.add_argument("--scenario", choices=["step", "sine", "lost", "noisy"], default="step")
    simulate.add_argument("--duration", type=float, default=15.0)
    simulate.add_argument("--fps", type=float, default=15.0)
    simulate.add_argument("--seed", type=int, default=0)
    simulate.add_argument("--az-step", type=float, default=20.0)
    simulate.add_argument("--el-step", type=float, default=0.0)
    simulate.add_argument("--step-time", type=float, default=2.0)
    simulate.add_argument("--az-amp", type=float, default=20.0)
    simulate.add_argument("--el-amp", type=float, default=0.0)
    simulate.add_argument("--period", type=float, default=8.0)
    simulate.add_argument("--lost-start", type=float, default=3.0)
    simulate.add_argument("--lost-duration", type=float, default=5.0)
    simulate.add_argument("--noise-deg", type=float, default=0.0)
    simulate.add_argument("--report-json", default=None)

    replay = sub.add_parser("replay", parents=[common], help="Replay a JSONL session")
    replay.add_argument("--input", required=True)
    replay.add_argument("--compare", action="store_true")
    replay.add_argument("--report-json", default=None)

    detect = sub.add_parser(
        "detect", parents=[common], help="Run a detector on an image/video/webcam"
    )
    detect.add_argument("--source", required=True, help="image:path | video:path | webcam:N")
    detect.add_argument("--detector", choices=["auto", "yunet", "mediapipe"], default="auto")
    detect.add_argument("--annotate", default=None, help="Write an annotated image")
    detect.add_argument("--flip", choices=["none", "horizontal", "vertical", "both"], default=None)

    calibrate = sub.add_parser("calibrate", parents=[common], help="Calibrate fatigue thresholds")
    calibrate_sub = calibrate.add_subparsers(dest="calibrate_command", required=True)
    ear = calibrate_sub.add_parser("ear", parents=[common])
    ear.add_argument("--source", default="webcam:0")
    ear.add_argument("--duration", type=float, default=10.0)
    ear.add_argument("--output", default="var/ear_calibration.json")
    ear.add_argument("--min-samples", type=int, default=10)

    doctor = sub.add_parser("doctor", parents=[common], help="Check environment and hardware")
    doctor.add_argument("--strict", action="store_true")
    doctor.add_argument("--probe-camera", action="store_true")
    doctor.add_argument("--probe-actuator", action="store_true")

    selftest = sub.add_parser("selftest", parents=[common], help="Run no-hardware self tests")
    selftest.add_argument("--quick", action="store_true")

    models = sub.add_parser("models", parents=[common], help="Download/verify model files")
    models_sub = models.add_subparsers(dest="models_command", required=True)
    download = models_sub.add_parser("download", parents=[common])
    download_group = download.add_mutually_exclusive_group()
    download_group.add_argument("--only", choices=["yunet", "mediapipe"], default=None)
    download_group.add_argument("--all", action="store_true", help="Download all models (default)")
    download.add_argument("--dest", default=None)
    download.add_argument("--force", action="store_true")
    verify = models_sub.add_parser("verify", parents=[common])
    verify_group = verify.add_mutually_exclusive_group()
    verify_group.add_argument("--only", choices=["yunet", "mediapipe"], default=None)
    verify_group.add_argument("--all", action="store_true", help="Verify all models (default)")
    verify.add_argument("--dest", default=None)

    sub.add_parser("info", parents=[common], help="Show version/config/capability summary")
    return parser


def _prepare_model_dir(args: argparse.Namespace) -> None:
    if args.model_dir:
        os.environ["AVFM_MODEL_DIR"] = args.model_dir


def _load(args: argparse.Namespace) -> AppConfig:
    _prepare_model_dir(args)
    overrides: dict[str, Any] = {}
    for attr, key in (
        ("source", "camera.source"),
        ("flip", "camera.flip"),
        ("fps", "runtime.fps"),
        ("width", "camera.width"),
        ("height", "camera.height"),
        ("detector", "detector.backend"),
        ("detector_mode", "detector.mode"),
        ("tracking_backend", "detector.tracking_backend"),
        ("fatigue_backend", "detector.fatigue_backend"),
        ("detect_interval", "detector.interval_frames"),
        ("tracking_interval", "detector.tracking_interval_frames"),
        ("fatigue_interval", "detector.fatigue_interval_frames"),
        ("servo", "actuator.backend"),
        ("calibration_file", "fatigue.ear_calibration_file"),
    ):
        value = getattr(args, attr, None)
        if value is not None:
            overrides[key] = value
    if getattr(args, "fps", None) is not None:
        overrides["camera.fps"] = args.fps
    if getattr(args, "show", None) is not None:
        overrides["runtime.show"] = args.show
    if getattr(args, "no_fatigue", False):
        overrides["fatigue.enabled"] = False
        if getattr(args, "detector_mode", None) == "split":
            overrides["detector.fatigue_backend"] = "none"
    return load_config(args.config, args.profile, overrides)


def _json_default(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return str(value)


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=_json_default))


def _write_json(path: str | None, data: Any) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8"
    )


def _resolve_single_backend(config: AppConfig) -> str:
    backend = config.detector.backend
    if backend != "auto":
        return backend
    root = model_root()
    if mediapipe_available() and model_ready(MEDIAPIPE, config.detector.mediapipe_model, root):
        return "mediapipe"
    if model_ready(YUNET, config.detector.yunet_model, root):
        return "yunet"
    raise DependencyMissingError(
        "No detector is available. Run: avfm models download --all "
        "or install the mediapipe extra: pip install -e '.[mediapipe]'"
    )


def _default_run_dir() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return Path("var") / "runs" / stamp


def _report_text(report: RunReport) -> str:
    return (
        f"frames={report.frames} dropped={report.dropped_frames} "
        f"loop_fps={report.loop_fps:.1f} tracking_hz={report.tracking_hz:.1f} "
        f"fatigue_hz={report.fatigue_hz:.1f} avg_loop_ms={report.avg_loop_ms:.1f} "
        f"p95_loop_ms={report.p95_loop_ms:.1f} "
        f"face_lost={report.face_lost_count} drowsy={report.drowsy_count} "
        f"distracted={report.distracted_count} errors={report.errors} mode={report.mode}"
    )


def cmd_run(args: argparse.Namespace) -> int:
    config = _load(args)
    if args.dry_run:
        _print_json(config.to_dict())
        return 0
    setup_logging(args.log_level or config.runtime.log_level)
    detectors = create_detectors(config.detector)
    actuator = create_actuator(
        config.actuator,
        config.gimbal,
        park_angles=(config.tracker.default_pan, config.tracker.default_tilt),
    )
    if actuator.fallback_reason:
        print(f"warning: actuator fallback: {actuator.fallback_reason}", file=sys.stderr)

    calibration = None
    calibration_file = args.calibration_file or config.fatigue.ear_calibration_file
    if calibration_file:
        try:
            calibration = EarCalibration.load(calibration_file)
        except Exception as exc:
            logger.warning("could not load calibration %s: %s", calibration_file, exc)

    record_dir = args.record_dir or (str(_default_run_dir()) if args.record_video else None)
    recorder: Any = NullRecorder()
    if record_dir:
        recorder = SessionRecorder(
            record_dir,
            config=config,
            source=config.camera.source,
            detector=f"{detectors.mode}:{detectors.tracking_name}/{detectors.fatigue_name}",
            actuator=actuator.actual_backend,
            fps=config.runtime.fps,
            frame_size=(config.camera.width, config.camera.height),
            record_video=args.record_video,
        )

    source = create_source(config.camera, realtime=args.realtime)
    pipeline = Pipeline(
        config,
        detectors,
        actuator,
        recorder=recorder,
        calibration=calibration,
    )
    show = config.runtime.show if args.show is None else args.show
    report = Runner().run(
        source,
        pipeline,
        duration=args.duration,
        max_frames=args.max_frames,
        target_fps=config.runtime.fps,
        show=show,
        realtime=args.realtime,
        record_video=args.record_video,
    )
    data = report.to_dict()
    data["actuator_fallback"] = actuator.fallback_reason
    _write_json(args.report_json, data)
    if args.json:
        _print_json(data)
    else:
        print(_report_text(report))
        if record_dir:
            print(f"session: {record_dir}")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    config = _load(args)
    setup_logging(args.log_level or config.runtime.log_level)
    scenario = Scenario(
        name=args.scenario,
        az_step=args.az_step,
        el_step=args.el_step,
        step_time=args.step_time,
        az_amp=args.az_amp,
        el_amp=args.el_amp,
        period=args.period,
        lost_start=args.lost_start if args.scenario == "lost" else None,
        lost_duration=args.lost_duration,
        noise_deg=args.noise_deg if args.scenario == "noisy" else 0.0,
    )
    report = run_simulation(scenario, config, duration=args.duration, fps=args.fps, seed=args.seed)
    data = report.to_dict()
    _write_json(args.report_json, data)
    if args.json:
        _print_json(data)
    else:
        print(
            f"{report.scenario}: settled={report.settled} settle={report.settle_time_s} "
            f"overshoot={report.overshoot:.3f} rmse={report.rmse:.3f} "
            f"max_error={report.max_error:.3f} final_error={report.final_error:.3f} "
            f"search={report.search_started} reacquire={report.reacquire_time_s}"
        )
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    config = _load(args)
    setup_logging(args.log_level or config.runtime.log_level)
    data = replay_session(args.input, config, compare=args.compare)
    _write_json(args.report_json, data)
    _print_json(data) if args.json else print(
        f"observations={data['observations']} events={len(data['events'])} "
        f"commands={len(data['commands'])}"
    )
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    config = _load(args)
    setup_logging(args.log_level or config.runtime.log_level)
    camera = dataclasses.replace(
        config.camera,
        source=args.source,
        flip=args.flip or config.camera.flip,
    )
    source = create_source(camera)
    source.open()
    try:
        frame = source.read()
        if frame is None:
            raise AvfmError(f"No frame from {args.source}")
        backend = args.detector if args.detector != "auto" else _resolve_single_backend(config)
        running_mode = "IMAGE" if args.source.startswith("image:") else "VIDEO"
        detector = create_detector(backend, config.detector, running_mode=running_mode)
        try:
            detections = detector.detect(frame)
            rows = []
            for detection in detections:
                row: dict[str, Any] = {
                    "bbox": [
                        detection.bbox.x,
                        detection.bbox.y,
                        detection.bbox.w,
                        detection.bbox.h,
                    ],
                    "score": detection.score,
                    "detector": detection.detector,
                    "frame_size": list(frame.frame_size),
                }
                if detection.landmarks is not None:
                    camera_model = CameraModel.from_fov(*frame.frame_size, config.camera.hfov_deg)
                    from avfm.types import FaceObservation

                    metrics = compute_face_metrics(
                        FaceObservation(detection, frame.frame_size, frame.timestamp),
                        camera_model,
                        max_reproj_error_px=config.fatigue.max_reproj_error_px,
                    )
                    row["ear"] = metrics.ear
                    row["yaw"] = metrics.yaw
                    row["pitch"] = metrics.pitch
                    row["roll"] = metrics.roll
                    row["valid_landmarks"] = metrics.valid_landmarks
                    row["valid_pose"] = metrics.valid_pose
                rows.append(row)
        finally:
            detector.close()
        if args.annotate:
            annotated = frame.image.copy()
            for detection in detections:
                x, y, w, h = (int(v) for v in detection.bbox.to_pixels(frame.frame_size))
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 220, 0), 2)
            Path(args.annotate).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(args.annotate, annotated)
        data = {"source": args.source, "detections": rows}
        if args.json:
            _print_json(data)
        else:
            print(f"{len(rows)} face(s) in {args.source}")
            for row in rows:
                print(json.dumps(row, ensure_ascii=False))
        return 0
    finally:
        source.close()


def cmd_calibrate(args: argparse.Namespace) -> int:
    config = _load(args)
    setup_logging(args.log_level or config.runtime.log_level)
    camera = dataclasses.replace(config.camera, source=args.source)
    source = create_source(camera)
    source.open()
    samples: list[float] = []
    try:
        detector = create_detector("mediapipe", config.detector, running_mode="VIDEO")
        duration = max(1.0, args.duration)
        first_ts: float | None = None
        try:
            while True:
                frame = source.read()
                if frame is None:
                    break
                if first_ts is None:
                    first_ts = frame.timestamp
                detections = detector.detect(frame)
                if detections and detections[0].landmarks is not None:
                    ear = compute_ear(detections[0].landmarks, frame.frame_size)
                    if ear.valid:
                        samples.append(ear.ear)
                if frame.timestamp - first_ts >= duration:
                    break
        finally:
            detector.close()
    finally:
        source.close()
    if not samples:
        raise AvfmError("No valid EAR samples were collected. Check lighting/camera and try again.")
    calibration = EarCalibration.from_samples(
        samples,
        source=args.source,
        frame_size=(config.camera.width, config.camera.height),
        min_samples=args.min_samples,
    )
    calibration.save(args.output)
    data = calibration.to_dict()
    if args.json:
        _print_json(data)
    else:
        print(
            f"EAR baseline={calibration.baseline:.3f} threshold={calibration.threshold:.3f} "
            f"samples={calibration.samples} -> {args.output}"
        )
    return 0


def _strict_doctor_ok(config: AppConfig, capabilities: list) -> bool:
    available = {capability.name: capability.available for capability in capabilities}
    required = ["opencv", "numpy"]
    if config.detector.mode == "single":
        backend = config.detector.backend
        if backend == "yunet":
            required.append("yunet_model")
        elif backend == "mediapipe":
            required.extend(["mediapipe", "mediapipe_model"])
        elif backend == "auto" and not (
            available.get("yunet_model", False)
            or (available.get("mediapipe", False) and available.get("mediapipe_model", False))
        ):
            return False
    else:
        if config.detector.tracking_backend == "yunet":
            required.append("yunet_model")
        elif config.detector.tracking_backend == "mediapipe":
            required.extend(["mediapipe", "mediapipe_model"])
        elif config.detector.tracking_backend == "auto" and not (
            available.get("yunet_model", False)
            or (available.get("mediapipe", False) and available.get("mediapipe_model", False))
        ):
            return False
        if config.fatigue.enabled and config.detector.fatigue_backend in {"mediapipe", "auto"}:
            required.extend(["mediapipe", "mediapipe_model"])
    if config.actuator.backend == "pca9685":
        required.append("adafruit_servokit")
    return all(available.get(name, False) for name in required)


def cmd_doctor(args: argparse.Namespace) -> int:
    config = _load(args)
    setup_logging(args.log_level or config.runtime.log_level)
    capabilities = collect_capabilities(
        config,
        probe_camera_device=args.probe_camera,
        probe_actuator=args.probe_actuator,
    )
    data = {
        "ok": _strict_doctor_ok(config, capabilities) if args.strict else True,
        "capabilities": [capability.to_dict() for capability in capabilities],
    }
    if args.json:
        _print_json(data)
    else:
        for capability in capabilities:
            mark = "OK " if capability.available else "MISS"
            print(f"[{mark}] {capability.name:22s} {capability.detail}")
            if not capability.available and capability.hint:
                print(f"       hint: {capability.hint}")
    return 0 if data["ok"] else 1


def cmd_selftest(args: argparse.Namespace) -> int:
    config = _load(args)
    setup_logging(args.log_level or config.runtime.log_level)
    duration = 8.0 if args.quick else 15.0
    lost_config = dataclasses.replace(
        config,
        tracker=dataclasses.replace(config.tracker, lost_timeout_s=2.0, hold_last_s=0.2),
    )
    step = run_simulation(Scenario(name="step"), config, duration=duration)
    sine = run_simulation(Scenario(name="sine"), config, duration=duration)
    lost = run_simulation(
        Scenario(name="lost", lost_start=3.0, lost_duration=5.0),
        lost_config,
        duration=max(12.0, duration),
    )
    checks = {
        "step_settled": bool(step.settled and step.final_error < 0.05),
        "step_overshoot": step.overshoot < 0.25,
        "sine_rmse": sine.rmse < 0.1,
        "lost_search": bool(lost.search_started and lost.reacquire_time_s is not None),
    }
    data = {
        "checks": checks,
        "reports": {"step": step.to_dict(), "sine": sine.to_dict(), "lost": lost.to_dict()},
    }
    if args.json:
        _print_json(data)
    else:
        for name, ok in checks.items():
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    return 0 if all(checks.values()) else 1


def cmd_models(args: argparse.Namespace) -> int:
    _prepare_model_dir(args)
    root = Path(args.dest) if getattr(args, "dest", None) else None
    if args.models_command == "download":
        paths = download_all(root, only=args.only, force=args.force)
        data = {"downloaded": [str(path) for path in paths]}
        _print_json(data) if args.json else [print(f"downloaded: {path}") for path in paths]
        return 0
    status = verify_all(root, only=args.only)
    if args.json:
        _print_json(status)
    else:
        for name, ok in status.items():
            print(f"[{'OK' if ok else 'MISS'}] {name}")
    return 0 if all(status.values()) else 1


def cmd_info(args: argparse.Namespace) -> int:
    config = _load(args)
    capabilities = collect_capabilities(config)
    data = {
        "version": __version__,
        "platform": platform.platform(),
        "python": sys.version,
        "config_files": list(config.loaded_from),
        "model_root": str(model_root()),
        "models": {
            "yunet": str(resolve_model_path(YUNET, config.detector.yunet_model)),
            "mediapipe": str(resolve_model_path(MEDIAPIPE, config.detector.mediapipe_model)),
        },
        "capabilities": [capability.to_dict() for capability in capabilities],
    }
    _print_json(data) if args.json else print(
        f"avfm {__version__} | {platform.platform()}\n"
        f"config: {config.loaded_from or 'code defaults'}\n"
        f"models: {data['models']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return cmd_run(args)
        if args.command == "simulate":
            return cmd_simulate(args)
        if args.command == "replay":
            return cmd_replay(args)
        if args.command == "detect":
            return cmd_detect(args)
        if args.command == "calibrate":
            return cmd_calibrate(args)
        if args.command == "doctor":
            return cmd_doctor(args)
        if args.command == "selftest":
            return cmd_selftest(args)
        if args.command == "models":
            return cmd_models(args)
        if args.command == "info":
            return cmd_info(args)
        parser.print_help()
        return 0
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except AvfmError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - unexpected
        logging.getLogger("avfm.cli").exception("unexpected error: %s", exc)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
