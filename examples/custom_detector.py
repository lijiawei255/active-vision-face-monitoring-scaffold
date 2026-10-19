"""How to plug in your own detector.

Implement the FaceDetector protocol and return normalised boxes. This example
returns a fixed box and is not a real detector.
"""

from __future__ import annotations

from avfm.detection.base import FaceDetector
from avfm.types import BBox, FaceDetection, Frame


class FixedDetector(FaceDetector):
    name = "fixed"
    supports_landmarks = False

    def detect(self, frame: Frame) -> list[FaceDetection]:
        width, height = frame.frame_size
        return [
            FaceDetection(
                bbox=BBox(0.4, 0.3, 0.2, 0.2),
                landmarks=None,
                score=1.0,
                detector=self.name,
            )
        ]

    def close(self) -> None:
        return None


# Then use it where create_detectors would normally return a DetectorSet:
# DetectorSet(tracking=FixedDetector(), fatigue=None, mode="single",
#             tracking_interval_frames=1, fatigue_interval_frames=1)
