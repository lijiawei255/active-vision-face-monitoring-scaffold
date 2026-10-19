from __future__ import annotations

import pytest


@pytest.mark.hardware
def test_picamera2_capture() -> None:
    from avfm.capture.picamera2 import Picamera2FrameSource

    source = Picamera2FrameSource(width=640, height=480, fps=15, flip="vertical")
    source.open()
    try:
        frame = source.read()
        assert frame is not None
        assert frame.image.shape[2] == 3
    finally:
        source.close()


@pytest.mark.hardware
def test_pca9685_sweep() -> None:
    from avfm.actuation.pca9685 import PCA9685Servo

    pan = PCA9685Servo(2, angle_min=40, angle_max=180, name="pan")
    pan.initialize()
    try:
        for angle in (60, 90, 120, 90):
            pan.set_angle(angle)
            assert pan.get_angle() == angle
    finally:
        pan.close()
