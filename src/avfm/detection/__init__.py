"""Face detectors."""

from avfm.detection.base import FaceDetector, select_primary
from avfm.detection.factory import DetectorSet, create_detector, create_detectors

__all__ = [
    "FaceDetector",
    "select_primary",
    "DetectorSet",
    "create_detector",
    "create_detectors",
]
