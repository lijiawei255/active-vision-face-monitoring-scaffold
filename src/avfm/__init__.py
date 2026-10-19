"""Active Vision Face Monitoring scaffold.

This package deliberately keeps optional dependencies (MediaPipe, Picamera2,
Adafruit ServoKit) out of the top-level import graph. Importing :mod:`avfm`
must work on a plain Python + NumPy + OpenCV installation.
"""

from __future__ import annotations

from importlib import metadata

try:  # pragma: no cover - exercised by installed package and editable install
    __version__ = metadata.version("avfm")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.1.2"

__all__ = ["__version__"]
