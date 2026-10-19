"""Head pose (yaw/pitch/roll) from six MediaPipe landmarks via solvePnP."""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from avfm.metrics.camera_model import CameraModel
from avfm.metrics.ear import landmarks_to_pixels
from avfm.types import Landmark

# Six standard face model points in millimetres. The Y axis points down to
# match the OpenCV image coordinate convention, so a frontal face gives R~=I.
MODEL_POINTS = np.array(
    [
        (0.0, 0.0, 0.0),  # nose tip
        (0.0, 63.6, -12.5),  # chin
        (-34.0, -32.6, -24.2),  # left outer eye corner
        (34.0, -32.6, -24.2),  # right outer eye corner
        (-28.5, 28.0, -11.8),  # left mouth corner
        (28.5, 28.0, -11.8),  # right mouth corner
    ],
    dtype=np.float64,
)

# nose tip, chin, left outer eye, right outer eye, left mouth, right mouth.
# These must be the OUTER eye corners; using the inner corners gives a
# systematic ~50 degree yaw bias because the model's eye separation is wide.
HEAD_POSE_INDICES = (1, 152, 33, 263, 61, 291)
_MAX_POSE_INDEX = max(HEAD_POSE_INDICES)


@dataclass(frozen=True, slots=True)
class HeadPose:
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    valid: bool = False
    reproj_error: float = float("inf")


def _euler_from_rotation(rotation: np.ndarray) -> tuple[float, float, float]:
    """Return (yaw, pitch, roll) in degrees for R = Rz * Ry * Rx."""
    sy = math.sqrt(rotation[0, 0] ** 2 + rotation[1, 0] ** 2)
    if sy > 1e-6:
        yaw = math.atan2(-rotation[2, 0], sy)
        pitch = math.atan2(rotation[2, 1], rotation[2, 2])
        roll = math.atan2(rotation[1, 0], rotation[0, 0])
    else:  # gimbal lock
        yaw = math.atan2(-rotation[2, 0], sy)
        pitch = math.atan2(-rotation[1, 2], rotation[1, 1])
        roll = 0.0
    return math.degrees(yaw), math.degrees(pitch), math.degrees(roll)


def estimate_head_pose(
    landmarks: tuple[Landmark, ...] | None,
    frame_size: tuple[int, int],
    camera_model: CameraModel,
    *,
    max_reproj_error_px: float = 20.0,
) -> HeadPose:
    if landmarks is None or len(landmarks) <= _MAX_POSE_INDEX:
        return HeadPose(valid=False)
    points = landmarks_to_pixels(landmarks, frame_size)
    image_points = np.array([points[index] for index in HEAD_POSE_INDICES], dtype=np.float64)
    camera_matrix = camera_model.matrix()
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    rvec = tvec = None
    for flag in (cv2.SOLVEPNP_SQPNP, cv2.SOLVEPNP_ITERATIVE):
        try:
            ok, rvec_candidate, tvec_candidate = cv2.solvePnP(
                MODEL_POINTS, image_points, camera_matrix, dist_coeffs, flags=flag
            )
        except cv2.error:
            continue
        if ok:
            rvec, tvec = rvec_candidate, tvec_candidate
            break
    if rvec is None or tvec is None:
        return HeadPose(valid=False)

    try:
        rotation, _ = cv2.Rodrigues(rvec)
        projected, _ = cv2.projectPoints(MODEL_POINTS, rvec, tvec, camera_matrix, dist_coeffs)
    except cv2.error:
        return HeadPose(valid=False)

    reproj_error = float(np.mean(np.linalg.norm(projected.reshape(-1, 2) - image_points, axis=1)))
    yaw, pitch, roll = _euler_from_rotation(rotation)
    if not all(math.isfinite(value) for value in (yaw, pitch, roll, reproj_error)):
        return HeadPose(valid=False)
    return HeadPose(
        yaw=yaw,
        pitch=pitch,
        roll=roll,
        valid=reproj_error <= max_reproj_error_px,
        reproj_error=reproj_error,
    )
