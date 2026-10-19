from __future__ import annotations

import pytest

from avfm.metrics.ear import LEFT_EYE, RIGHT_EYE, compute_ear, landmarks_to_pixels
from tests.helpers import make_eye_landmarks


def test_open_eyes_ear() -> None:
    landmarks = make_eye_landmarks(left_ear=0.3, right_ear=0.3)
    metrics = compute_ear(landmarks, (640, 480))
    assert metrics.valid
    assert metrics.ear == pytest.approx(0.3, rel=1e-6)
    assert metrics.left_ear == pytest.approx(0.3, rel=1e-6)
    assert metrics.right_ear == pytest.approx(0.3, rel=1e-6)


def test_closed_eyes_lower_ear() -> None:
    landmarks = make_eye_landmarks(left_ear=0.02, right_ear=0.02)
    metrics = compute_ear(landmarks, (640, 480))
    assert metrics.valid
    assert metrics.ear < 0.05


def test_one_eye_invalid_uses_other() -> None:
    landmarks = make_eye_landmarks(left_ear=0.3, right_ear=0.2, left_valid=False)
    metrics = compute_ear(landmarks, (640, 480))
    assert metrics.valid
    assert not metrics.left_valid
    assert metrics.right_valid
    assert metrics.ear == pytest.approx(0.2, rel=1e-6)


def test_missing_landmarks_invalid() -> None:
    assert not compute_ear(None, (640, 480)).valid
    assert not compute_ear((), (640, 480)).valid


def test_landmarks_to_pixels_uses_frame_extent() -> None:
    landmarks = make_eye_landmarks()
    points = landmarks_to_pixels(landmarks, (640, 480))
    assert points.shape == (478, 2)
    # The left eye centre should be around 0.35 * width.
    assert points[LEFT_EYE[0]][0] < points[RIGHT_EYE[0]][0]
