"""CLI coverage for text/JSON output, fallbacks, error codes and fakes.

The happy paths are already covered in ``test_cli.py``/``test_cli_extra.py``;
this module exercises the branches that a normal run rarely hits: actuator
fallback, default recording directories, calibration, annotation, strict
doctor failures and clean error reporting.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import avfm.cli as cli
from avfm.capture.base import FrameSource
from avfm.cli import main
from avfm.detection.base import FaceDetector
from avfm.detection.factory import DetectorSet
from avfm.detection.fake import FakeDetector
from avfm.types import BBox, FaceDetection, Frame, RunReport
from tests.helpers import REPO_ROOT, make_eye_landmarks, make_frame

ASTRONAUT = REPO_ROOT / "tests" / "data" / "astronaut.jpg"
YUNET_MODEL = REPO_ROOT / "models" / "yunet" / "face_detection_yunet_2026may.onnx"


class ListSource(FrameSource):
    """Replay a fixed frame list, then report end-of-stream."""

    def __init__(self, frames: list[Frame]) -> None:
        self._frames = list(frames)
        self._cursor = 0

    def open(self) -> None:
        return None

    def read(self) -> Frame | None:
        if self._cursor >= len(self._frames):
            return None
        frame = self._frames[self._cursor]
        self._cursor += 1
        return frame

    def close(self) -> None:
        return None

    @property
    def description(self) -> str:
        return "image:fake"


def _write_image(tmp_path: Path) -> Path:
    import cv2

    path = tmp_path / "frame.jpg"
    cv2.imwrite(str(path), np.zeros((48, 64, 3), dtype=np.uint8))
    return path


def _fake_detectors(detector: FaceDetector | None = None) -> DetectorSet:
    tracking = detector or FakeDetector(
        [[FaceDetection(BBox(0.4, 0.3, 0.2, 0.2), None, 1.0, "fake")]]
    )
    return DetectorSet(
        tracking=tracking,
        fatigue=None,
        mode="single",
        tracking_interval_frames=1,
        fatigue_interval_frames=1,
    )


def _landmark_detector() -> FakeDetector:
    landmarks = make_eye_landmarks()
    return FakeDetector(
        lambda frame: [
            FaceDetection(BBox(0.3, 0.3, 0.4, 0.4), landmarks, 1.0, "fake"),
        ]
    )


def test_run_text_output_report_and_recording(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    image = _write_image(tmp_path)
    monkeypatch.setattr(cli, "create_detectors", lambda config: _fake_detectors())
    session_dir = tmp_path / "session"
    report_path = tmp_path / "report.json"
    rc = main(
        [
            "run",
            "--source",
            f"image:{image}",
            "--detector",
            "yunet",
            "--servo",
            "none",
            "--no-show",
            "--record-dir",
            str(session_dir),
            "--report-json",
            str(report_path),
            "--calibration-file",
            str(tmp_path / "missing-calibration.json"),
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "frames=1" in captured.out
    assert "session:" in captured.out
    assert "could not load calibration" not in captured.out  # warning goes to the logger
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["frames"] == 1
    assert (session_dir / "session.jsonl").exists()
    assert (session_dir / "run.json").exists()


def test_run_auto_actuator_falls_back_to_passive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    image = _write_image(tmp_path)

    def failing_pca_pair(*args: object, **kwargs: object) -> None:
        raise RuntimeError("no I2C bus in CI")

    monkeypatch.setattr("avfm.actuation.factory._pca_pair", failing_pca_pair)
    monkeypatch.setattr(cli, "create_detectors", lambda config: _fake_detectors())
    rc = main(
        [
            "run",
            "--source",
            f"image:{image}",
            "--servo",
            "auto",
            "--no-show",
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "actuator fallback" in captured.err
    data = json.loads(captured.out)
    assert data["actuator_fallback"]


def test_run_record_video_uses_default_run_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = _write_image(tmp_path)
    monkeypatch.setattr(cli, "create_detectors", lambda config: _fake_detectors())
    monkeypatch.setattr(cli, "_default_run_dir", lambda: tmp_path / "auto-run")
    rc = main(
        [
            "run",
            "--source",
            f"image:{image}",
            "--servo",
            "none",
            "--no-show",
            "--record-video",
            "--max-frames",
            "1",
            "--json",
        ]
    )
    assert rc == 0
    assert (tmp_path / "auto-run" / "annotated.mp4").exists()


def test_run_dry_run_no_fatigue_split(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--dry-run", "--json", "--no-fatigue", "--detector-mode", "split"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["fatigue"]["enabled"] is False
    assert data["detector"]["fatigue_backend"] == "none"


def test_info_model_dir_and_text_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Register the variable with monkeypatch first so teardown restores it even
    # though the CLI assigns os.environ directly.
    monkeypatch.setenv("AVFM_MODEL_DIR", "placeholder")
    model_dir = tmp_path / "models"
    assert main(["info", "--model-dir", str(model_dir), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["model_root"].endswith("models")
    assert main(["info"]) == 0
    assert "avfm" in capsys.readouterr().out


def test_models_download_and_verify_text(capsys: pytest.CaptureFixture[str]) -> None:
    if not YUNET_MODEL.exists():
        pytest.skip("YuNet model not downloaded")
    assert main(["models", "download", "--only", "yunet"]) == 0
    assert "downloaded:" in capsys.readouterr().out
    assert main(["models", "verify", "--only", "yunet"]) == 0
    assert "[OK] yunet" in capsys.readouterr().out


def test_doctor_text_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor"]) == 0
    assert "[OK " in capsys.readouterr().out


def test_doctor_strict_fails_on_missing_optional_requirements(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_file = tmp_path / "strict.toml"
    config_file.write_text(
        '[detector]\nmode = "single"\nbackend = "mediapipe"\n[actuator]\nbackend = "pca9685"\n',
        encoding="utf-8",
    )
    assert main(["doctor", "--json", "--strict", "--config", str(config_file)]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is False


def test_simulate_text_and_report_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report_path = tmp_path / "simulation.json"
    assert (
        main(
            [
                "simulate",
                "--scenario",
                "step",
                "--duration",
                "3",
                "--report-json",
                str(report_path),
            ]
        )
        == 0
    )
    assert "settled=" in capsys.readouterr().out
    assert json.loads(report_path.read_text(encoding="utf-8"))["frames"] > 0


def test_selftest_text_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["selftest", "--quick"]) == 0
    assert "[PASS]" in capsys.readouterr().out


@pytest.mark.model
def test_detect_auto_backend_annotation_and_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if not YUNET_MODEL.exists():
        pytest.skip("YuNet model not downloaded")
    annotated = tmp_path / "annotated.png"
    assert main(["detect", "--source", f"image:{ASTRONAUT}", "--annotate", str(annotated)]) == 0
    captured = capsys.readouterr()
    assert "face(s) in" in captured.out
    assert annotated.exists()


def test_detect_landmark_metrics(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    detector = _landmark_detector()
    monkeypatch.setattr(cli, "create_detector", lambda backend, config, **kwargs: detector)
    monkeypatch.setattr(
        cli, "create_source", lambda camera, clock=None, **kwargs: ListSource([make_frame()])
    )
    assert main(["detect", "--source", "image:fake", "--detector", "yunet", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    row = data["detections"][0]
    assert row["detector"] == "fake"
    assert row["valid_landmarks"] is True
    assert "ear" in row


def test_detect_no_frame_returns_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "create_source", lambda camera, clock=None, **kwargs: ListSource([]))
    assert main(["detect", "--source", "image:fake", "--detector", "yunet"]) == 2
    assert "No frame" in capsys.readouterr().err


def test_calibrate_ear_with_fake_camera(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    frames = [make_frame(timestamp=index * 0.02) for index in range(12)]
    detector = _landmark_detector()
    monkeypatch.setattr(
        cli, "create_source", lambda camera, clock=None, **kwargs: ListSource(frames)
    )
    monkeypatch.setattr(cli, "create_detector", lambda backend, config, **kwargs: detector)
    output = tmp_path / "ear_calibration.json"
    rc = main(
        [
            "calibrate",
            "ear",
            "--source",
            "image:fake",
            "--duration",
            "0.05",
            "--output",
            str(output),
            "--min-samples",
            "3",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "EAR baseline=" in captured.out
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["samples"] >= 3


def test_main_reports_config_errors_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["run", "--dry-run", "--config", str(tmp_path / "missing.toml")]) == 2
    assert "error:" in capsys.readouterr().err


def test_main_returns_130_on_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    def interrupt(args: object) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "cmd_run", interrupt)
    assert main(["run"]) == 130


def test_write_json_falls_back_to_to_dict_and_str(tmp_path: Path) -> None:
    target = tmp_path / "fallback.json"
    cli._write_json(str(target), {"report": RunReport(frames=2), "path": Path("z")})
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["report"]["frames"] == 2
    assert data["path"] == "z"
