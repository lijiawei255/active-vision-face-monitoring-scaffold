"""Frame capture backends."""

from avfm.capture.base import FrameSource, apply_flip
from avfm.capture.factory import create_source

__all__ = ["FrameSource", "apply_flip", "create_source"]
