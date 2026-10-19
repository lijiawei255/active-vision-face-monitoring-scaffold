from __future__ import annotations

import numpy as np
import pytest

from avfm import capabilities
from avfm.config import AppConfig


def test_collect_capabilities(config: AppConfig) -> None:
    caps = capabilities.collect_capabilities(config)
    names = {capability.name for capability in caps}
    assert {"python", "numpy", "opencv", "yunet_model", "mediapipe_model"} <= names
    assert all(capability.detail for capability in caps)


def test_doctor_dict(config: AppConfig) -> None:
    data = capabilities.doctor_dict(config)
    assert data["ok"] is True
    assert isinstance(data["capabilities"], list)


def test_probe_camera_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCapture:
        def __init__(self, index: int) -> None:
            self.index = index

        def isOpened(self) -> bool:
            return self.index == 0

        def read(self):
            return True, np.zeros((10, 10, 3), dtype=np.uint8)

        def release(self) -> None:
            pass

    monkeypatch.setattr(capabilities.cv2, "VideoCapture", FakeCapture)
    capability = capabilities.probe_camera()
    assert capability.available
    assert "10x10" in capability.detail


def test_probe_camera_none(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCapture:
        def __init__(self, index: int) -> None:
            self.index = index

        def isOpened(self) -> bool:
            return False

        def read(self):
            return False, None

        def release(self) -> None:
            pass

    monkeypatch.setattr(capabilities.cv2, "VideoCapture", FakeCapture)
    capability = capabilities.probe_camera()
    assert not capability.available
