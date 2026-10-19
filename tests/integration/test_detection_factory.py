from __future__ import annotations

from pathlib import Path

import pytest

from avfm.config import DetectorConfig
from avfm.detection.factory import create_detector, create_detectors
from avfm.errors import DependencyMissingError, ModelNotFoundError

REPO_ROOT = Path(__file__).resolve().parents[2]
YUNET_MODEL = REPO_ROOT / "models" / "yunet" / "face_detection_yunet_2026may.onnx"
MEDIAPIPE_MODEL = REPO_ROOT / "models" / "mediapipe" / "face_landmarker.task"


def test_single_yunet_factory() -> None:
    if not YUNET_MODEL.exists():
        pytest.skip("YuNet model not downloaded")
    detectors = create_detectors(DetectorConfig(mode="single", backend="yunet"))
    try:
        assert detectors.mode == "single"
        assert detectors.tracking.name == "yunet"
        assert detectors.fatigue is None
    finally:
        detectors.close()


@pytest.mark.mediapipe
def test_split_factory() -> None:
    if not YUNET_MODEL.exists() or not MEDIAPIPE_MODEL.exists():
        pytest.skip("models not downloaded")
    detectors = create_detectors(
        DetectorConfig(
            mode="split",
            tracking_backend="yunet",
            fatigue_backend="mediapipe",
            tracking_interval_frames=1,
            fatigue_interval_frames=2,
        )
    )
    try:
        assert detectors.tracking.name == "yunet"
        assert detectors.fatigue is not None
        assert detectors.fatigue.name == "mediapipe"
    finally:
        detectors.close()


def test_missing_yunet_model(tmp_path: Path) -> None:
    config = DetectorConfig(
        mode="single", backend="yunet", yunet_model=str(tmp_path / "missing.onnx")
    )
    with pytest.raises(ModelNotFoundError):
        create_detector("yunet", config)


def test_mediapipe_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import avfm.detection.factory as factory

    monkeypatch.setattr(factory, "mediapipe_available", lambda: False)
    config = DetectorConfig(
        mode="single", backend="mediapipe", mediapipe_model=str(tmp_path / "missing.task")
    )
    with pytest.raises(DependencyMissingError):
        create_detector("mediapipe", config)
