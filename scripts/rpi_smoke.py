#!/usr/bin/env python
"""Raspberry Pi smoke test: camera, optional servo sweep, short pipeline run.

Run this on the Pi after wiring. It is intentionally interactive before moving
servos. The JSON report is written to ``var/hil_report.json`` by default.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from avfm.capabilities import collect_capabilities
from avfm.capture.factory import create_source
from avfm.config import load_config


def _run_pipeline(profile: str, servo: str, duration: float, output: Path) -> dict:
    command = [
        sys.executable,
        "-m",
        "avfm",
        "run",
        "--source",
        "picamera",
        "--servo",
        servo,
        "--config",
        f"configs/{profile}.toml",
        "--no-show",
        "--duration",
        str(duration),
        "--record-dir",
        str(output),
        "--json",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    report = {}
    run_json = output / "run.json"
    if run_json.exists():
        report = json.loads(run_json.read_text(encoding="utf-8"))
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip()[-4000:],
        "report": report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="rpi")
    parser.add_argument("--no-servo", action="store_true", help="Force passive mode")
    parser.add_argument("--duration", type=float, default=15.0)
    parser.add_argument("--output", default="var/hil_report.json")
    parser.add_argument("--yes", action="store_true", help="Do not prompt before moving servos")
    args = parser.parse_args()

    config = load_config(profile=args.profile)
    capabilities = [capability.to_dict() for capability in collect_capabilities(config)]
    report: dict = {
        "kind": "rpi_smoke",
        "created_at": datetime.now(UTC).isoformat(),
        "profile": args.profile,
        "capabilities": capabilities,
    }

    # Camera probe + one frame.
    source = create_source(config.camera)
    try:
        source.open()
        frame = source.read()
        report["camera"] = {
            "opened": True,
            "frame_shape": list(frame.image.shape) if frame is not None else None,
        }
    except Exception as exc:
        report["camera"] = {"opened": False, "error": str(exc)}
    finally:
        source.close()

    # Optional physical servo sweep. Never move without an explicit confirmation.
    if not args.no_servo:
        if not args.yes and input("Move servos for a small sweep? [y/N] ").strip().lower() != "y":
            report["servo_sweep"] = {"skipped": True}
        else:
            try:
                from avfm.actuation.pca9685 import PCA9685Servo

                pan = PCA9685Servo(
                    config.actuator.pan_channel,
                    angle_min=config.gimbal.pan_min,
                    angle_max=config.gimbal.pan_max,
                    name="pan",
                )
                tilt = PCA9685Servo(
                    config.actuator.tilt_channel,
                    angle_min=config.gimbal.tilt_min,
                    angle_max=config.gimbal.tilt_max,
                    name="tilt",
                )
                pan.initialize()
                tilt.initialize()
                for angle in (
                    config.tracker.default_pan,
                    config.tracker.default_pan + 10,
                    config.tracker.default_pan - 10,
                    config.tracker.default_pan,
                ):
                    pan.set_angle(angle)
                for angle in (
                    config.tracker.default_tilt,
                    config.tracker.default_tilt + 5,
                    config.tracker.default_tilt,
                ):
                    tilt.set_angle(angle)
                pan.close()
                tilt.close()
                report["servo_sweep"] = {"ok": True}
            except Exception as exc:
                report["servo_sweep"] = {"ok": False, "error": str(exc)}
    else:
        report["servo_sweep"] = {"skipped": True, "reason": "--no-servo"}

    # Short pipeline run, passive if no servos were requested.
    servo = "none" if args.no_servo else "pca9685"
    output = Path("var") / "hil" / f"smoke-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    report["pipeline"] = _run_pipeline(args.profile, servo, args.duration, output)

    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("camera", {}).get("opened") else 1


if __name__ == "__main__":
    raise SystemExit(main())
