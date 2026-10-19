"""Scriptable detector used by tests, examples and SIL scenarios."""

from __future__ import annotations

from collections.abc import Callable

from avfm.detection.base import FaceDetector
from avfm.types import FaceDetection, Frame


class FakeDetector(FaceDetector):
    """Return scripted detections and count invocations.

    ``script`` may be a callable ``(frame) -> list[FaceDetection]`` or a list
    of detection lists consumed one item per call. When the script is
    exhausted an empty detection list is returned.
    """

    supports_landmarks = True

    def __init__(
        self,
        script: Callable[[Frame], list[FaceDetection]] | list[list[FaceDetection]] | None = None,
        *,
        name: str = "fake",
    ) -> None:
        self.name = name
        self._script = script
        self._cursor = 0
        self.calls = 0
        self.frames: list[Frame] = []

    def detect(self, frame: Frame) -> list[FaceDetection]:
        self.calls += 1
        self.frames.append(frame)
        if callable(self._script):
            return self._script(frame)
        if isinstance(self._script, list):
            if self._cursor < len(self._script):
                result = self._script[self._cursor]
                self._cursor += 1
                return result
            return []
        return []

    def close(self) -> None:
        return None
