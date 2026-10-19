"""Detector factory for single and split perception modes."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

from avfm.config import DetectorConfig
from avfm.detection.base import FaceDetector
from avfm.detection.mediapipe import MediaPipeDetector
from avfm.detection.yunet import YuNetDetector
from avfm.errors import DependencyMissingError, ModelNotFoundError
from avfm.models import MEDIAPIPE, YUNET, ModelSpec, model_root, resolve_model_path

_DOWNLOAD_HINT = "Run: avfm models download --all  (or --only yunet / --only mediapipe)"


@dataclass
class DetectorSet:
    tracking: FaceDetector
    fatigue: FaceDetector | None
    mode: str
    tracking_interval_frames: int
    fatigue_interval_frames: int

    @property
    def tracking_name(self) -> str:
        return self.tracking.name

    @property
    def fatigue_name(self) -> str:
        return self.fatigue.name if self.fatigue is not None else "none"

    def close(self) -> None:
        closed: set[int] = set()
        for detector in (self.tracking, self.fatigue):
            if detector is None or id(detector) in closed:
                continue
            detector.close()
            closed.add(id(detector))


def mediapipe_available() -> bool:
    return importlib.util.find_spec("mediapipe") is not None


def model_ready(spec: ModelSpec, configured: str | Path | None, root: Path | None = None) -> bool:
    path = resolve_model_path(spec, configured, root)
    return path.exists()


def create_detector(
    backend: str,
    config: DetectorConfig,
    *,
    root: Path | None = None,
    running_mode: str = "VIDEO",
) -> FaceDetector:
    base = root if root is not None else model_root()
    if backend == "yunet":
        path = resolve_model_path(YUNET, config.yunet_model, base)
        if not path.exists():
            raise ModelNotFoundError(f"YuNet model not found at {path}. {_DOWNLOAD_HINT}")
        return YuNetDetector(
            path,
            score_threshold=config.score_threshold,
            nms_threshold=config.nms_threshold,
            max_faces=config.max_faces,
        )
    if backend == "mediapipe":
        if not mediapipe_available():
            raise DependencyMissingError(
                "mediapipe is not installed. Run: pip install -e '.[mediapipe]'"
            )
        path = resolve_model_path(MEDIAPIPE, config.mediapipe_model, base)
        if not path.exists():
            raise ModelNotFoundError(f"MediaPipe model not found at {path}. {_DOWNLOAD_HINT}")
        return MediaPipeDetector(
            path,
            running_mode=running_mode,
            max_faces=config.max_faces,
            min_detection_confidence=config.min_detection_confidence,
            min_presence_confidence=config.min_presence_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
    raise ValueError(f"Unknown detector backend: {backend}")


def _auto_tracking_backend(config: DetectorConfig, root: Path) -> str:
    if model_ready(YUNET, config.yunet_model, root):
        return "yunet"
    if mediapipe_available() and model_ready(MEDIAPIPE, config.mediapipe_model, root):
        return "mediapipe"
    raise DependencyMissingError(
        "No face detector is available. Install mediapipe and/or download a model. "
        + _DOWNLOAD_HINT
    )


def _auto_fatigue_backend(config: DetectorConfig, root: Path) -> str:
    if mediapipe_available() and model_ready(MEDIAPIPE, config.mediapipe_model, root):
        return "mediapipe"
    return "none"


def create_detectors(config: DetectorConfig, *, root: Path | None = None) -> DetectorSet:
    base = root if root is not None else model_root()
    if config.mode == "single":
        backend = config.backend
        if backend == "auto":
            if mediapipe_available() and model_ready(MEDIAPIPE, config.mediapipe_model, base):
                backend = "mediapipe"
            elif model_ready(YUNET, config.yunet_model, base):
                backend = "yunet"
            else:
                raise DependencyMissingError(
                    "No face detector is available. Install mediapipe and/or download a model. "
                    + _DOWNLOAD_HINT
                )
        detector = create_detector(backend, config, root=base)
        fatigue = detector if detector.supports_landmarks else None
        return DetectorSet(
            tracking=detector,
            fatigue=fatigue,
            mode="single",
            tracking_interval_frames=config.interval_frames,
            fatigue_interval_frames=config.interval_frames,
        )

    tracking_backend = config.tracking_backend
    if tracking_backend == "auto":
        tracking_backend = _auto_tracking_backend(config, base)
    fatigue_backend = config.fatigue_backend
    if fatigue_backend == "auto":
        fatigue_backend = _auto_fatigue_backend(config, base)

    tracking = create_detector(tracking_backend, config, root=base)
    if fatigue_backend == "none":
        fatigue = None
    elif fatigue_backend == tracking_backend:
        fatigue = tracking
    else:
        fatigue = create_detector(fatigue_backend, config, root=base)

    return DetectorSet(
        tracking=tracking,
        fatigue=fatigue,
        mode="split",
        tracking_interval_frames=config.tracking_interval_frames,
        fatigue_interval_frames=config.fatigue_interval_frames,
    )
