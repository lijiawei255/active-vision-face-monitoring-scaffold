"""Metric computation for a face observation."""

from __future__ import annotations

from avfm.metrics.camera_model import CameraModel
from avfm.metrics.ear import EyeMetrics, compute_ear
from avfm.metrics.head_pose import HeadPose, estimate_head_pose
from avfm.types import FaceMetrics, FaceObservation


def compute_face_metrics(
    observation: FaceObservation,
    camera_model: CameraModel,
    *,
    max_reproj_error_px: float = 20.0,
) -> FaceMetrics:
    landmarks = observation.detection.landmarks
    if landmarks is None:
        return FaceMetrics(timestamp=observation.timestamp)
    ear: EyeMetrics = compute_ear(landmarks, observation.frame_size)
    pose: HeadPose = estimate_head_pose(
        landmarks,
        observation.frame_size,
        camera_model,
        max_reproj_error_px=max_reproj_error_px,
    )
    return FaceMetrics(
        ear=ear.ear,
        left_ear=ear.left_ear,
        right_ear=ear.right_ear,
        yaw=pose.yaw,
        pitch=pose.pitch,
        roll=pose.roll,
        valid_landmarks=ear.valid,
        valid_pose=pose.valid,
        reproj_error=pose.reproj_error,
        timestamp=observation.timestamp,
    )


__all__ = ["CameraModel", "compute_face_metrics", "compute_ear", "estimate_head_pose"]
