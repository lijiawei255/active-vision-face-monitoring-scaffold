from __future__ import annotations

from avfm.actuation.factory import create_actuator
from avfm.app.overlay import OverlayRenderer
from avfm.app.pipeline import Pipeline
from avfm.config import AppConfig
from avfm.detection.factory import DetectorSet
from avfm.detection.fake import FakeDetector
from avfm.types import BBox, FaceDetection
from tests.helpers import make_eye_landmarks, make_frame


def test_overlay_with_landmarks_and_fatigue(config: AppConfig) -> None:
    landmarks = make_eye_landmarks(left_ear=0.3, right_ear=0.3)
    detection = FaceDetection(BBox(0.4, 0.3, 0.2, 0.2), landmarks, 1.0, "fake")
    detector = FakeDetector([[detection]])
    detectors = DetectorSet(
        tracking=detector,
        fatigue=detector,
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
    result = pipeline.process_frame(make_frame(timestamp=0.0))
    rendered = OverlayRenderer().draw(result.frame.image, result, mode="passive")
    assert rendered.shape == result.frame.image.shape
    assert result.fatigue is not None
    assert result.metrics is not None
    pipeline.close()
