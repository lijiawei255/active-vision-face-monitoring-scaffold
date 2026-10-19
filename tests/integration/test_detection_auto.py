from __future__ import annotations

import pytest

from avfm.config import DetectorConfig
from avfm.detection.factory import create_detectors


def test_auto_single_without_mediapipe(monkeypatch: pytest.MonkeyPatch) -> None:
    import avfm.detection.factory as factory

    monkeypatch.setattr(factory, "mediapipe_available", lambda: False)
    detectors = create_detectors(DetectorConfig(mode="single", backend="auto"))
    try:
        assert detectors.tracking.name == "yunet"
        assert detectors.fatigue is None
    finally:
        detectors.close()


def test_auto_split_without_mediapipe(monkeypatch: pytest.MonkeyPatch) -> None:
    import avfm.detection.factory as factory

    monkeypatch.setattr(factory, "mediapipe_available", lambda: False)
    detectors = create_detectors(
        DetectorConfig(mode="split", tracking_backend="auto", fatigue_backend="auto")
    )
    try:
        assert detectors.tracking.name == "yunet"
        assert detectors.fatigue is None
    finally:
        detectors.close()
