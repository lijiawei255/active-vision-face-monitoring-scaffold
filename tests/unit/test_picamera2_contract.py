from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from avfm.capture.picamera2 import Picamera2FrameSource
from avfm.clock import FakeClock
from avfm.errors import DependencyMissingError


def test_picamera2_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCamera:
        def __init__(self) -> None:
            self.started = False
            self.closed = False

        def create_video_configuration(self, main, controls):
            self.main = main
            self.controls = controls
            return {"main": main, "controls": controls}

        def configure(self, configuration):
            self.configuration = configuration

        def start(self) -> None:
            self.started = True

        def capture_array(self):
            return np.zeros((10, 20, 3), dtype=np.uint8)

        def stop(self) -> None:
            self.started = False

        def close(self) -> None:
            self.closed = True

    fake_module = types.ModuleType("picamera2")
    fake_module.Picamera2 = FakeCamera  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "picamera2", fake_module)
    clock = FakeClock()
    source = Picamera2FrameSource(
        width=20,
        height=10,
        fps=15,
        flip="none",
        warmup_s=0.5,
        clock=clock,
    )
    source.open()
    assert clock.sleeps == [0.5]
    frame = source.read()
    assert frame is not None
    assert frame.image.shape == (10, 20, 3)
    source.close()


def test_picamera2_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "picamera2", None)
    source = Picamera2FrameSource(width=20, height=10, fps=15)
    with pytest.raises(DependencyMissingError):
        source.open()
