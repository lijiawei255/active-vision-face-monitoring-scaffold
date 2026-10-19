from __future__ import annotations

import pytest

from avfm.app.runner import Runner
from avfm.capture.base import FrameSource
from avfm.clock import FakeClock
from avfm.errors import CameraError
from avfm.types import Frame


class EmptyLiveSource(FrameSource):
    def open(self) -> None:
        return None

    def read(self) -> Frame | None:
        return None

    def close(self) -> None:
        return None

    @property
    def description(self) -> str:
        return "webcam:99"


def test_runner_raises_after_repeated_live_failures(config) -> None:
    from avfm.actuation.factory import create_actuator
    from avfm.app.pipeline import Pipeline
    from avfm.detection.factory import DetectorSet
    from avfm.detection.fake import FakeDetector

    detector = FakeDetector()
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
    pipeline = Pipeline(config, detectors, actuator)
    clock = FakeClock()
    with pytest.raises(CameraError):
        Runner(clock=clock).run(EmptyLiveSource(), pipeline, show=False)
    assert len(clock.sleeps) >= 19
