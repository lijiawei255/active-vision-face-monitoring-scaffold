"""Single and split perception cadence.

The parent project ran a fast tracking detector every frame and MediaPipe every
few frames. This module preserves that separation while allowing a single
detector for desktop use.
"""

from __future__ import annotations

import time

from avfm.detection.factory import DetectorSet
from avfm.types import FaceDetection, FaceObservation, Frame, PerceptionResult


class Perception:
    def __init__(self, detectors: DetectorSet) -> None:
        self.detectors = detectors
        self.tracking_calls = 0
        self.fatigue_calls = 0

    def _observation(self, detections: list[FaceDetection], frame: Frame) -> FaceObservation | None:
        if not detections:
            return None
        return FaceObservation(
            detection=detections[0],
            frame_size=frame.frame_size,
            timestamp=frame.timestamp,
        )

    def process(self, frame: Frame, frame_index: int) -> PerceptionResult:
        tracking_ran = frame_index % self.detectors.tracking_interval_frames == 0
        fatigue = self.detectors.fatigue
        fatigue_ran = (
            fatigue is not None and frame_index % self.detectors.fatigue_interval_frames == 0
        )

        if not tracking_ran and not fatigue_ran:
            return PerceptionResult()

        same_detector = fatigue is not None and fatigue is self.detectors.tracking
        tracking_ms = 0.0
        fatigue_ms = 0.0

        if same_detector:
            started = time.perf_counter()
            detections = self.detectors.tracking.detect(frame)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            if tracking_ran:
                self.tracking_calls += 1
                tracking_ms = elapsed_ms
            if fatigue_ran:
                self.fatigue_calls += 1
                fatigue_ms = elapsed_ms
            tracking_obs = self._observation(detections, frame)
            fatigue_obs = tracking_obs
            return PerceptionResult(
                tracking_obs=tracking_obs if tracking_ran else None,
                fatigue_obs=fatigue_obs if fatigue_ran else None,
                tracking_ran=tracking_ran,
                fatigue_ran=fatigue_ran,
                tracking_detect_ms=tracking_ms,
                fatigue_detect_ms=fatigue_ms,
            )

        tracking_obs = None
        if tracking_ran:
            started = time.perf_counter()
            tracking_obs = self._observation(self.detectors.tracking.detect(frame), frame)
            tracking_ms = (time.perf_counter() - started) * 1000.0
            self.tracking_calls += 1

        fatigue_obs = None
        if fatigue_ran and fatigue is not None:
            started = time.perf_counter()
            fatigue_obs = self._observation(fatigue.detect(frame), frame)
            fatigue_ms = (time.perf_counter() - started) * 1000.0
            self.fatigue_calls += 1

        return PerceptionResult(
            tracking_obs=tracking_obs,
            fatigue_obs=fatigue_obs,
            tracking_ran=tracking_ran,
            fatigue_ran=fatigue_ran,
            tracking_detect_ms=tracking_ms,
            fatigue_detect_ms=fatigue_ms,
        )

    def close(self) -> None:
        self.detectors.close()
