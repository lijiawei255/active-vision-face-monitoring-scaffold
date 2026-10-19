"""Detector protocol and shared selection helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from avfm.types import FaceDetection, Frame


class FaceDetector(ABC):
    """A face detector with a BGR-frame contract."""

    name: str = "detector"
    supports_landmarks: bool = False

    @abstractmethod
    def detect(self, frame: Frame) -> list[FaceDetection]: ...

    @abstractmethod
    def close(self) -> None: ...


def select_primary(detections: list[FaceDetection], max_faces: int = 1) -> list[FaceDetection]:
    """Pick the largest faces, breaking ties by closeness to the frame centre."""
    ranked = sorted(
        detections,
        key=lambda det: (
            det.bbox.area,
            -(abs(det.bbox.cx - 0.5) + abs(det.bbox.cy - 0.5)),
        ),
        reverse=True,
    )
    return ranked[: max(1, max_faces)]
