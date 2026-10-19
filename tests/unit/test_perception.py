from __future__ import annotations

from avfm.detection.factory import DetectorSet
from avfm.detection.fake import FakeDetector
from avfm.perception.pipeline import Perception
from avfm.types import BBox, FaceDetection
from tests.helpers import make_frame


def detection() -> list[FaceDetection]:
    return [FaceDetection(BBox(0.4, 0.3, 0.2, 0.2), None, 1.0, "fake")]


def test_split_cadence() -> None:
    tracking = FakeDetector([detection() for _ in range(10)])
    fatigue = FakeDetector([detection() for _ in range(10)])
    perception = Perception(
        DetectorSet(
            tracking=tracking,
            fatigue=fatigue,
            mode="split",
            tracking_interval_frames=2,
            fatigue_interval_frames=3,
        )
    )
    frame = make_frame(timestamp=0.0)
    for index in range(4):
        frame = make_frame(timestamp=index / 15.0)
        result = perception.process(frame, index)
        assert result.tracking_ran == (index % 2 == 0)
        assert result.fatigue_ran == (index % 3 == 0)
    assert tracking.calls == 2
    assert fatigue.calls == 2


def test_same_detector_is_called_once() -> None:
    shared = FakeDetector([detection() for _ in range(10)])
    perception = Perception(
        DetectorSet(
            tracking=shared,
            fatigue=shared,
            mode="single",
            tracking_interval_frames=1,
            fatigue_interval_frames=2,
        )
    )
    perception.process(make_frame(timestamp=0.0), 0)
    perception.process(make_frame(timestamp=1 / 15), 1)
    assert shared.calls == 2


def test_skipped_frame_returns_no_observation() -> None:
    tracking = FakeDetector([detection()])
    fatigue = FakeDetector([detection()])
    perception = Perception(
        DetectorSet(
            tracking=tracking,
            fatigue=fatigue,
            mode="split",
            tracking_interval_frames=3,
            fatigue_interval_frames=5,
        )
    )
    result = perception.process(make_frame(timestamp=0.0), 1)
    assert not result.tracking_ran
    assert not result.fatigue_ran
    assert tracking.calls == 0
    assert fatigue.calls == 0
