"""Eye Aspect Ratio (EAR) from MediaPipe Face Mesh landmarks.

EAR is computed in pixel space. Using normalised coordinates directly would
distort the ratio on non-square images, because x and y are normalised by
different extents.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from avfm.types import Landmark

# MediaPipe Face Mesh eye contour indices (same indices for the 478-point mesh).
LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)
_MAX_EYE_INDEX = max(LEFT_EYE + RIGHT_EYE)


@dataclass(frozen=True, slots=True)
class EyeMetrics:
    left_ear: float
    right_ear: float
    ear: float
    valid: bool
    left_valid: bool
    right_valid: bool


def landmarks_to_pixels(landmarks: tuple[Landmark, ...], frame_size: tuple[int, int]) -> np.ndarray:
    width, height = frame_size
    return np.array(
        [[lm.x * width, lm.y * height] for lm in landmarks],
        dtype=np.float64,
    )


def _ear_for_indices(points: np.ndarray, indices: tuple[int, ...]) -> float:
    p = points[list(indices)]
    vertical = np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])
    horizontal = 2.0 * np.linalg.norm(p[0] - p[3])
    if horizontal <= 1e-9:
        return float("nan")
    return float(vertical / horizontal)


def compute_ear(landmarks: tuple[Landmark, ...] | None, frame_size: tuple[int, int]) -> EyeMetrics:
    if landmarks is None or len(landmarks) <= _MAX_EYE_INDEX:
        return EyeMetrics(0.0, 0.0, 0.0, False, False, False)
    points = landmarks_to_pixels(landmarks, frame_size)
    left = _ear_for_indices(points, LEFT_EYE)
    right = _ear_for_indices(points, RIGHT_EYE)
    left_valid = np.isfinite(left) and left > 0
    right_valid = np.isfinite(right) and right > 0
    values = [value for value, ok in ((left, left_valid), (right, right_valid)) if ok]
    if not values:
        return EyeMetrics(0.0, 0.0, 0.0, False, False, False)
    return EyeMetrics(
        left_ear=float(left) if left_valid else 0.0,
        right_ear=float(right) if right_valid else 0.0,
        ear=float(sum(values) / len(values)),
        valid=True,
        left_valid=bool(left_valid),
        right_valid=bool(right_valid),
    )
