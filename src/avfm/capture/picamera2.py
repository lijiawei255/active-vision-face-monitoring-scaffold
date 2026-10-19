"""Raspberry Pi Picamera2 source. Optional dependency, imported lazily."""

from __future__ import annotations

import contextlib
import logging

import cv2

from avfm.capture.base import FrameSource, apply_flip
from avfm.clock import Clock, MonotonicClock
from avfm.errors import CameraError, DependencyMissingError
from avfm.types import Frame

logger = logging.getLogger("avfm.capture.picamera2")


class Picamera2FrameSource(FrameSource):
    """OV5647 / Picamera2 source.

    The camera is configured for RGB888 and converted to the project-wide BGR
    contract. Import failures produce an actionable apt/pip hint.
    """

    def __init__(
        self,
        *,
        width: int,
        height: int,
        fps: float,
        flip: str = "none",
        warmup_s: float = 0.5,
        clock: Clock | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.flip = flip
        self.warmup_s = warmup_s
        self.clock = clock or MonotonicClock()
        self._camera = None
        self._index = 0
        self._opened = False

    def open(self) -> None:
        try:
            from picamera2 import Picamera2
        except ImportError as exc:
            raise DependencyMissingError(
                "picamera2 is not available. On Raspberry Pi OS run: "
                "sudo apt install -y python3-picamera2  "
                "(or install the optional extra: pip install -e '.[rpi]')"
            ) from exc

        camera = None
        try:
            camera = Picamera2()
            video_config = camera.create_video_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"},
                controls={"FrameRate": self.fps},
            )
            camera.configure(video_config)
            camera.start()
            if self.warmup_s > 0:
                self.clock.sleep(self.warmup_s)
        except Exception as exc:
            if camera is not None:
                with contextlib.suppress(Exception):
                    camera.stop()
                with contextlib.suppress(Exception):
                    camera.close()
            raise CameraError(
                "Could not start Picamera2. Check that the CSI camera is enabled "
                "(libcamera-hello --list-cameras) and not used by another process."
            ) from exc
        self._camera = camera
        self._opened = True

    def read(self) -> Frame | None:
        if not self._opened or self._camera is None:
            raise CameraError("Picamera2 source is not open")
        try:
            rgb = self._camera.capture_array()
            if rgb.ndim != 3 or rgb.shape[2] != 3:
                if rgb.ndim == 3 and rgb.shape[2] == 4:
                    image = cv2.cvtColor(rgb, cv2.COLOR_RGBA2BGR)
                else:
                    logger.warning("Unexpected Picamera2 frame shape: %s", rgb.shape)
                    return None
            else:
                image = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception as exc:
            logger.warning("Picamera2 capture failed: %s", exc)
            return None
        image = apply_flip(image, self.flip)
        frame = Frame(
            image=image,
            timestamp=self.clock.now(),
            index=self._index,
            source=self.description,
        )
        self._index += 1
        return frame

    def close(self) -> None:
        if self._camera is not None:
            with contextlib.suppress(Exception):
                self._camera.stop()
            with contextlib.suppress(Exception):
                self._camera.close()
            self._camera = None
        self._opened = False

    @property
    def description(self) -> str:
        return f"picamera:{self.width}x{self.height}@{self.fps:g}"
