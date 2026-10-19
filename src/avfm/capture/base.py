"""Capture abstractions and shared frame transforms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

import cv2
import numpy as np

from avfm.types import Frame

_FLIP_CODES = {"horizontal": 1, "vertical": 0, "both": -1}


def apply_flip(image: np.ndarray, flip: str) -> np.ndarray:
    """Apply the configured camera orientation correction."""
    if flip == "none":
        return image
    code = _FLIP_CODES.get(flip)
    if code is None:
        raise ValueError(f"Unsupported flip mode: {flip}")
    return cv2.flip(image, code)


class FrameSource(ABC):
    """A source of BGR frames with monotonic timestamps."""

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def read(self) -> Frame | None:
        """Return the next frame, or None at end-of-stream / transient failure."""

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
