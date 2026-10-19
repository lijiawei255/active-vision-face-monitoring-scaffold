from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from avfm.actuation.factory import create_actuator
from avfm.app.pipeline import Pipeline
from avfm.app.runner import Runner
from avfm.capture.opencv import OpenCVFrameSource
from avfm.config import AppConfig
from avfm.detection.factory import DetectorSet
from avfm.detection.fake import FakeDetector
from avfm.types import BBox, FaceDetection


def test_runner_image_end_of_stream(tmp_path: Path, config: AppConfig) -> None:
    image_path = tmp_path / "frame.jpg"
    cv2.imwrite(str(image_path), np.zeros((48, 64, 3), dtype=np.uint8))
    detector = FakeDetector([[FaceDetection(BBox(0.4, 0.3, 0.2, 0.2), None, 1.0, "fake")]])
    detectors = DetectorSet(
        tracking=detector,
        fatigue=FakeDetector(),
        mode="single",
        tracking_interval_frames=1,
        fatigue_interval_frames=1,
    )
    actuator = create_actuator(
        config.actuator,
        config.gimbal,
        park_angles=(config.tracker.default_pan, config.tracker.default_tilt),
    )
    pipeline = Pipeline(config, detectors, actuator)
    source = OpenCVFrameSource("image", str(image_path), width=64, height=48, fps=15, flip="none")
    report = Runner().run(source, pipeline, show=False, record_video=False)
    assert report.frames == 1
    assert report.loop_fps == 0.0
    assert detector.calls == 1


def _pipeline_for_show(config: AppConfig) -> Pipeline:
    detector = FakeDetector([[FaceDetection(BBox(0.4, 0.3, 0.2, 0.2), None, 1.0, "fake")]])
    detectors = DetectorSet(
        tracking=detector,
        fatigue=None,
        mode="single",
        tracking_interval_frames=1,
        fatigue_interval_frames=1,
    )
    actuator = create_actuator(
        config.actuator,
        config.gimbal,
        park_angles=(config.tracker.default_pan, config.tracker.default_tilt),
    )
    return Pipeline(config, detectors, actuator)


def test_runner_show_quits_on_q(
    tmp_path: Path, config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "frame.jpg"
    cv2.imwrite(str(image_path), np.zeros((48, 64, 3), dtype=np.uint8))
    pipeline = _pipeline_for_show(config)
    source = OpenCVFrameSource("image", str(image_path), width=64, height=48, fps=15, flip="none")
    monkeypatch.setattr(cv2, "imshow", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "waitKey", lambda *args, **kwargs: ord("q"))
    report = Runner().run(source, pipeline, show=True)
    assert report.frames == 1


def test_runner_show_unavailable_falls_back_to_headless(
    tmp_path: Path, config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    image_path = tmp_path / "frame.jpg"
    cv2.imwrite(str(image_path), np.zeros((48, 64, 3), dtype=np.uint8))
    pipeline = _pipeline_for_show(config)
    source = OpenCVFrameSource("image", str(image_path), width=64, height=48, fps=15, flip="none")

    def unavailable(*args: object, **kwargs: object) -> None:
        raise cv2.error("no GUI backend")

    monkeypatch.setattr(cv2, "imshow", unavailable)
    report = Runner().run(source, pipeline, show=True)
    assert report.frames == 1
