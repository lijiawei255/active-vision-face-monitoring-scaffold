"""Minimal desktop passive demo: webcam + no servos + optional window."""

from __future__ import annotations

from avfm.actuation.factory import create_actuator
from avfm.app.pipeline import Pipeline
from avfm.app.runner import Runner
from avfm.capture.factory import create_source
from avfm.config import load_config
from avfm.detection.factory import create_detectors


def main() -> int:
    config = load_config(profile="desktop")
    detectors = create_detectors(config.detector)
    actuator = create_actuator(
        config.actuator,
        config.gimbal,
        park_angles=(config.tracker.default_pan, config.tracker.default_tilt),
    )
    source = create_source(config.camera)
    pipeline = Pipeline(config, detectors, actuator)
    report = Runner().run(source, pipeline, duration=30.0, show=True)
    print(report.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
