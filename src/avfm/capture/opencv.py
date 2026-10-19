"""OpenCV-based sources: USB webcam, video file, still image."""

from __future__ import annotations

from pathlib import Path

import cv2

from avfm.capture.base import FrameSource, apply_flip
from avfm.clock import Clock, MonotonicClock
from avfm.errors import CameraError
from avfm.types import Frame


class OpenCVFrameSource(FrameSource):
    """Webcam / video / image source.

    ``kind`` is one of ``webcam``, ``video`` or ``image``. Video timestamps use
    ``frame_index / fps`` so replay is deterministic; webcam timestamps use a
    monotonic clock.
    """

    def __init__(
        self,
        kind: str,
        target: str | int,
        *,
        width: int,
        height: int,
        fps: float,
        flip: str = "none",
        realtime: bool = False,
        clock: Clock | None = None,
    ) -> None:
        if kind not in {"webcam", "video", "image"}:
            raise ValueError(f"Unsupported OpenCV source kind: {kind}")
        self.kind = kind
        self.target = target
        self.width = width
        self.height = height
        self.fps = fps
        self.flip = flip
        self.realtime = realtime
        self.clock = clock or MonotonicClock()
        self._cap: cv2.VideoCapture | None = None
        self._image = None
        self._index = 0
        self._file_fps = fps
        self._opened = False

    def open(self) -> None:
        if self.kind == "image":
            image = cv2.imread(str(self.target), cv2.IMREAD_COLOR)
            if image is None:
                raise CameraError(f"Could not read image: {self.target}")
            self._image = image
            self._opened = True
            return

        if self.kind == "webcam":
            path = int(self.target)
        else:
            path = str(self.target)
            if not Path(path).exists():
                raise CameraError(f"Video file not found: {path}")

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            cap.release()
            raise CameraError(
                f"Could not open {self.kind} source {self.target!r}. "
                "On Windows, check that the camera is not used by another app."
            )
        if self.kind == "video":
            # Read the file rate before touching properties; setting FPS/size on
            # a video capture can change or hide the real timing metadata.
            file_fps = cap.get(cv2.CAP_PROP_FPS)
            if file_fps and file_fps > 0:
                self._file_fps = float(file_fps)
        else:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.width))
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.height))
            cap.set(cv2.CAP_PROP_FPS, float(self.fps))
            # Keep only the latest frame in the driver queue.
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._cap = cap
        self._opened = True

    def read(self) -> Frame | None:
        if not self._opened:
            raise CameraError("Frame source is not open")
        if self.kind == "image":
            if self._index > 0:
                return None
            self._index += 1
            image = apply_flip(self._image, self.flip)
            return Frame(image=image, timestamp=0.0, index=0, source=self.description)

        assert self._cap is not None
        ok, image = self._cap.read()
        if not ok or image is None:
            return None

        if self.kind == "video":
            timestamp = self._index / max(self._file_fps, 1e-6)
        else:
            timestamp = self.clock.now()

        image = apply_flip(image, self.flip)
        frame = Frame(image=image, timestamp=timestamp, index=self._index, source=self.description)
        self._index += 1
        return frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._opened = False

    @property
    def description(self) -> str:
        return f"{self.kind}:{self.target}"
