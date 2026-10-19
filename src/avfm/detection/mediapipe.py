"""MediaPipe Face Landmarker (Tasks API) detector.

MediaPipe 0.10.31+ removed the legacy ``mp.solutions`` API; this module uses
``mp.tasks.vision.FaceLandmarker`` and a downloaded ``face_landmarker.task``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from avfm.detection.base import FaceDetector, select_primary
from avfm.errors import DependencyMissingError, DetectorError, ModelNotFoundError
from avfm.models import MEDIAPIPE, verify_model_or_raise
from avfm.types import BBox, FaceDetection, Frame, Landmark

logger = logging.getLogger("avfm.detection.mediapipe")


class MediaPipeDetector(FaceDetector):
    name = "mediapipe"
    supports_landmarks = True

    def __init__(
        self,
        model_path: str | Path,
        *,
        running_mode: str = "VIDEO",
        max_faces: int = 1,
        min_detection_confidence: float = 0.5,
        min_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        bbox_margin: float = 0.02,
    ) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise ModelNotFoundError(
                f"MediaPipe model not found at {self.model_path}. Run: "
                "avfm models download --only mediapipe"
            )
        verify_model_or_raise(MEDIAPIPE, self.model_path)
        self.running_mode = running_mode.upper()
        if self.running_mode not in {"VIDEO", "IMAGE"}:
            raise ValueError("running_mode must be VIDEO or IMAGE")
        self.max_faces = max_faces
        self.min_detection_confidence = min_detection_confidence
        self.min_presence_confidence = min_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.bbox_margin = bbox_margin
        self._landmarker = None
        self._mp = None
        self._last_ts_ms = -1

    def _ensure(self) -> None:
        if self._landmarker is not None:
            return
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise DependencyMissingError(
                "mediapipe is not installed. Run: pip install -e '.[mediapipe]'"
            ) from exc
        try:
            base_options = mp.tasks.BaseOptions(model_asset_path=str(self.model_path))
            options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=(
                    mp.tasks.vision.RunningMode.VIDEO
                    if self.running_mode == "VIDEO"
                    else mp.tasks.vision.RunningMode.IMAGE
                ),
                num_faces=self.max_faces,
                min_face_detection_confidence=self.min_detection_confidence,
                min_face_presence_confidence=self.min_presence_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
            )
            self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
            self._mp = mp
        except Exception as exc:
            raise DetectorError(f"Could not create MediaPipe FaceLandmarker: {exc}") from exc

    def detect(self, frame: Frame) -> list[FaceDetection]:
        self._ensure()
        assert self._landmarker is not None and self._mp is not None
        mp = self._mp
        rgb = cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        try:
            if self.running_mode == "VIDEO":
                timestamp_ms = max(self._last_ts_ms + 1, int(frame.timestamp * 1000.0))
                result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
                self._last_ts_ms = timestamp_ms
            else:
                result = self._landmarker.detect(mp_image)
        except Exception as exc:
            raise DetectorError(f"MediaPipe inference failed: {exc}") from exc

        detections: list[FaceDetection] = []
        for face_landmarks in result.face_landmarks or []:
            landmarks = tuple(
                Landmark(x=float(lm.x), y=float(lm.y), z=float(getattr(lm, "z", 0.0)))
                for lm in face_landmarks
            )
            if not landmarks:
                continue
            xs = [lm.x for lm in landmarks]
            ys = [lm.y for lm in landmarks]
            x0 = max(0.0, min(xs) - self.bbox_margin)
            y0 = max(0.0, min(ys) - self.bbox_margin)
            x1 = min(1.0, max(xs) + self.bbox_margin)
            y1 = min(1.0, max(ys) + self.bbox_margin)
            if x1 <= x0 or y1 <= y0:
                continue
            detections.append(
                FaceDetection(
                    bbox=BBox(x0, y0, x1 - x0, y1 - y0),
                    landmarks=landmarks,
                    score=1.0,
                    detector=self.name,
                )
            )
        return select_primary(detections, self.max_faces)

    def close(self) -> None:
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:  # pragma: no cover - native cleanup
                logger.exception("MediaPipe cleanup failed")
            self._landmarker = None
        self._mp = None
