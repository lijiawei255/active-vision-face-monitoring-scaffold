from __future__ import annotations

import pytest

from avfm.metrics.camera_model import CameraModel
from avfm.metrics.head_pose import estimate_head_pose
from tests.helpers import make_head_pose_landmarks


@pytest.mark.parametrize(("yaw", "pitch"), [(0.0, 0.0), (20.0, 0.0), (0.0, 15.0), (-15.0, 10.0)])
def test_synthetic_head_pose_roundtrip(yaw: float, pitch: float) -> None:
    frame_size = (640, 480)
    camera = CameraModel.from_fov(*frame_size, 60.0)
    landmarks = make_head_pose_landmarks(yaw, pitch, frame_size=frame_size)
    pose = estimate_head_pose(landmarks, frame_size, camera)
    assert pose.valid
    assert pose.yaw == pytest.approx(yaw, abs=1.0)
    assert pose.pitch == pytest.approx(pitch, abs=1.0)
    assert pose.reproj_error < 1.0


def test_missing_landmarks_invalid() -> None:
    camera = CameraModel.from_fov(640, 480, 60.0)
    assert not estimate_head_pose(None, (640, 480), camera).valid


def test_degenerate_landmarks_invalid_or_low_quality() -> None:
    camera = CameraModel.from_fov(640, 480, 60.0)
    from avfm.types import Landmark

    landmarks = tuple(Landmark(0.5, 0.5) for _ in range(478))
    pose = estimate_head_pose(landmarks, (640, 480), camera)
    assert not pose.valid or pose.reproj_error > 20.0
