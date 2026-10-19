"""Pinhole camera model derived from a horizontal field of view."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class CameraModel:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float

    @classmethod
    def from_fov(cls, width: int, height: int, hfov_deg: float) -> CameraModel:
        if width <= 0 or height <= 0:
            raise ValueError("Camera width/height must be positive")
        if not 0 < hfov_deg < 180:
            raise ValueError("hfov_deg must be between 0 and 180")
        fx = width / (2.0 * math.tan(math.radians(hfov_deg) / 2.0))
        return cls(
            width=width,
            height=height,
            fx=fx,
            fy=fx,  # square pixels
            cx=width / 2.0,
            cy=height / 2.0,
        )

    def matrix(self) -> np.ndarray:
        return np.array(
            [[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )
