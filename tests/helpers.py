"""Shared test fixtures and synthetic geometry helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from avfm.config import load_config
from avfm.types import BBox, FaceDetection, FaceMetrics, Frame, Landmark

REPO_ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-webcam", action="store_true", help="Enable local webcam tests")
    parser.addoption(
        "--run-hardware", action="store_true", help="Enable Raspberry Pi hardware tests"
    )
    parser.addoption("--run-mediapipe", action="store_true", help="Enable MediaPipe model tests")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        for marker, option in (
            ("webcam", "--run-webcam"),
            ("hardware", "--run-hardware"),
            ("mediapipe", "--run-mediapipe"),
        ):
            if item.get_closest_marker(marker) and not config.getoption(option):
                item.add_marker(pytest.mark.skip(reason=f"requires explicit {option}"))


@pytest.fixture
def config(tmp_path: Path):
    return load_config(cwd=tmp_path)


@pytest.fixture
def frame() -> Frame:
    return Frame(
        image=np.zeros((480, 640, 3), dtype=np.uint8),
        timestamp=0.0,
        index=0,
        source="test",
    )


def make_frame(width: int = 640, height: int = 480, timestamp: float = 0.0) -> Frame:
    return Frame(
        image=np.zeros((height, width, 3), dtype=np.uint8),
        timestamp=timestamp,
        index=0,
        source="test",
    )


def make_observation(
    bbox: tuple[float, float, float, float] = (0.4, 0.3, 0.2, 0.2),
    *,
    timestamp: float = 0.0,
    frame_size: tuple[int, int] = (640, 480),
    landmarks: tuple[Landmark, ...] | None = None,
) -> object:
    from avfm.types import FaceObservation

    return FaceObservation(
        detection=FaceDetection(bbox=BBox(*bbox), landmarks=landmarks, score=1.0, detector="test"),
        frame_size=frame_size,
        timestamp=timestamp,
    )


def make_metrics(
    *,
    ear: float = 0.3,
    yaw: float = 0.0,
    pitch: float = 0.0,
    roll: float = 0.0,
    valid_landmarks: bool = True,
    valid_pose: bool = True,
    timestamp: float = 0.0,
) -> FaceMetrics:
    return FaceMetrics(
        ear=ear,
        left_ear=ear,
        right_ear=ear,
        yaw=yaw,
        pitch=pitch,
        roll=roll,
        valid_landmarks=valid_landmarks,
        valid_pose=valid_pose,
        reproj_error=1.0 if valid_pose else float("inf"),
        timestamp=timestamp,
    )


def _set_eye(
    landmarks: list[Landmark],
    indices: tuple[int, ...],
    center_x: float,
    center_y: float,
    width_px: float,
    ear: float,
    *,
    frame_size: tuple[int, int],
    valid: bool = True,
) -> None:
    width, height = frame_size
    half = width_px / 2.0
    vertical = ear * width_px / 2.0
    if not valid:
        half = 0.0
        vertical = 0.0
    points = [
        (center_x - half, center_y),
        (center_x - half * 0.5, center_y - vertical),
        (center_x + half * 0.5, center_y - vertical),
        (center_x + half, center_y),
        (center_x + half * 0.5, center_y + vertical),
        (center_x - half * 0.5, center_y + vertical),
    ]
    for index, (x, y) in zip(indices, points, strict=True):
        landmarks[index] = Landmark(float(x) / width, float(y) / height)


def make_eye_landmarks(
    *,
    frame_size: tuple[int, int] = (640, 480),
    left_ear: float = 0.3,
    right_ear: float = 0.3,
    left_valid: bool = True,
    right_valid: bool = True,
) -> tuple[Landmark, ...]:
    from avfm.metrics.ear import LEFT_EYE, RIGHT_EYE

    width, height = frame_size
    landmarks = [Landmark(0.5, 0.5) for _ in range(478)]
    _set_eye(
        landmarks,
        LEFT_EYE,
        width * 0.35,
        height * 0.45,
        width * 0.10,
        left_ear,
        frame_size=frame_size,
        valid=left_valid,
    )
    _set_eye(
        landmarks,
        RIGHT_EYE,
        width * 0.65,
        height * 0.45,
        width * 0.10,
        right_ear,
        frame_size=frame_size,
        valid=right_valid,
    )
    return tuple(landmarks)


def make_head_pose_landmarks(
    yaw_deg: float,
    pitch_deg: float,
    *,
    frame_size: tuple[int, int] = (640, 480),
    hfov_deg: float = 60.0,
    tz: float = 500.0,
) -> tuple[Landmark, ...]:
    import cv2

    from avfm.metrics.camera_model import CameraModel
    from avfm.metrics.head_pose import HEAD_POSE_INDICES, MODEL_POINTS

    width, height = frame_size
    camera = CameraModel.from_fov(width, height, hfov_deg)
    rotation = cv2.Rodrigues(
        np.array([np.radians(pitch_deg), np.radians(yaw_deg), 0.0], dtype=np.float64)
    )[0]
    rvec, _ = cv2.Rodrigues(rotation)
    tvec = np.array([[0.0], [0.0], [tz]], dtype=np.float64)
    projected, _ = cv2.projectPoints(MODEL_POINTS, rvec, tvec, camera.matrix(), np.zeros((4, 1)))
    points = projected.reshape(-1, 2)
    landmarks = [Landmark(0.5, 0.5) for _ in range(478)]
    for index, (x, y) in zip(HEAD_POSE_INDICES, points, strict=True):
        landmarks[index] = Landmark(float(x) / width, float(y) / height)
    return tuple(landmarks)
