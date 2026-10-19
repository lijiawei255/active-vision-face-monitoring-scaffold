"""YuNet face detector using OpenCV's ``cv2.FaceDetectorYN``.

OpenCV 5 moved Haar/HOG to contrib and the pip wheels no longer ship
``cv2.data/haarcascades``; YuNet is the supported lightweight alternative and
lives in the core ``objdetect`` module.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2

from avfm.detection.base import FaceDetector, select_primary
from avfm.errors import DetectorError, ModelNotFoundError
from avfm.models import YUNET, verify_model_or_raise
from avfm.types import BBox, FaceDetection, Frame

logger = logging.getLogger("avfm.detection.yunet")


class YuNetDetector(FaceDetector):
    name = "yunet"
    supports_landmarks = False

    def __init__(
        self,
        model_path: str | Path,
        *,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        max_faces: int = 1,
        min_face_px: int = 20,
    ) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise ModelNotFoundError(
                f"YuNet model not found at {self.model_path}. Run: "
                "avfm models download --only yunet"
            )
        verify_model_or_raise(YUNET, self.model_path)
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.max_faces = max_faces
        self.min_face_px = min_face_px
        self._detector: cv2.FaceDetectorYN | None = None
        self._size: tuple[int, int] | None = None

    def _ensure(self, frame_size: tuple[int, int]) -> None:
        width, height = frame_size
        if self._detector is None:
            try:
                self._detector = cv2.FaceDetectorYN.create(
                    str(self.model_path),
                    "",
                    (width, height),
                    self.score_threshold,
                    self.nms_threshold,
                    5000,
                )
            except cv2.error as exc:
                raise DetectorError(f"Could not create YuNet detector: {exc}") from exc
            self._size = (width, height)
        elif self._size != (width, height):
            self._detector.setInputSize((width, height))
            self._size = (width, height)

    def detect(self, frame: Frame) -> list[FaceDetection]:
        self._ensure(frame.frame_size)
        assert self._detector is not None
        try:
            _, faces = self._detector.detect(frame.image)
        except cv2.error as exc:
            raise DetectorError(f"YuNet inference failed: {exc}") from exc
        if faces is None:
            return []
        detections: list[FaceDetection] = []
        frame_size = frame.frame_size
        for row in faces:
            x, y, w, h = (float(value) for value in row[:4])
            if w < self.min_face_px or h < self.min_face_px:
                continue
            detections.append(
                FaceDetection(
                    bbox=BBox.from_pixels(x, y, w, h, frame_size),
                    landmarks=None,
                    score=float(row[14]),
                    detector=self.name,
                )
            )
        return select_primary(detections, self.max_faces)

    def close(self) -> None:
        self._detector = None
        self._size = None
