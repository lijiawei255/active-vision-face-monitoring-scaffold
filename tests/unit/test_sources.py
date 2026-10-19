from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from avfm.capture.base import apply_flip
from avfm.capture.factory import create_source
from avfm.capture.opencv import OpenCVFrameSource
from avfm.clock import FakeClock
from avfm.config import CameraConfig
from avfm.errors import ConfigError


def test_apply_flip() -> None:
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    image[0:5] = 255
    flipped = apply_flip(image, "vertical")
    assert flipped[5:].sum() > 0
    with pytest.raises(ValueError):
        apply_flip(image, "sideways")


def test_image_source_and_end_of_stream(tmp_path: Path) -> None:
    path = tmp_path / "image.jpg"
    image = np.zeros((20, 30, 3), dtype=np.uint8)
    image[0:10] = 255
    assert cv2.imwrite(str(path), image)
    source = OpenCVFrameSource(
        "image",
        str(path),
        width=30,
        height=20,
        fps=15,
        flip="vertical",
    )
    source.open()
    try:
        frame = source.read()
        assert frame is not None
        assert frame.image.shape == (20, 30, 3)
        assert frame.timestamp == 0.0
        assert source.read() is None
    finally:
        source.close()


def test_create_source_image(tmp_path: Path) -> None:
    path = tmp_path / "image.jpg"
    cv2.imwrite(str(path), np.zeros((20, 30, 3), dtype=np.uint8))
    config = CameraConfig(source=f"image:{path}", width=30, height=20)
    source = create_source(config)
    assert source.description.startswith("image:")


def test_create_source_invalid() -> None:
    with pytest.raises(ConfigError):
        create_source(CameraConfig(source="unknown:0"))
    with pytest.raises(ConfigError):
        create_source(CameraConfig(source="video:missing.mp4"))


def test_fake_clock() -> None:
    clock = FakeClock()
    clock.sleep(1.5)
    assert clock.now() == 1.5
    clock.advance(0.5)
    assert clock.now() == 2.0
    with pytest.raises(ValueError):
        clock.sleep(-1)
