"""Loss-of-face horizontal search pattern."""

from __future__ import annotations

from avfm.config import GimbalConfig, TrackerConfig
from avfm.types import GimbalCommand


class SearchController:
    """Sweep the pan axis between limits; tilt stays at the configured angle."""

    def __init__(self, tracker: TrackerConfig, gimbal: GimbalConfig) -> None:
        self.tracker = tracker
        self.gimbal = gimbal
        self.active = False
        self.finished = False
        self._pan = tracker.default_pan
        self._tilt = min(max(tracker.scan_tilt_deg, gimbal.tilt_min), gimbal.tilt_max)
        self._direction = 1.0
        self._next_move = 0.0
        self._boundary_hits = 0

    def start(self, now: float, pan: float, tilt: float) -> None:
        self.active = True
        self.finished = False
        self._pan = min(max(pan, self.gimbal.pan_min), self.gimbal.pan_max)
        self._tilt = min(
            max(self.tracker.scan_tilt_deg, self.gimbal.tilt_min), self.gimbal.tilt_max
        )
        self._direction = 1.0
        self._next_move = now
        self._boundary_hits = 0

    def step(self, now: float) -> GimbalCommand:
        if not self.active:
            return GimbalCommand(self._pan, self._tilt, applied=False, reason="search")
        if now >= self._next_move:
            self._pan += self.tracker.scan_step_deg * self._direction
            if self._pan >= self.gimbal.pan_max:
                self._pan = self.gimbal.pan_max
                self._direction = -1.0
                self._boundary_hits += 1
            elif self._pan <= self.gimbal.pan_min:
                self._pan = self.gimbal.pan_min
                self._direction = 1.0
                self._boundary_hits += 1
            self._next_move = now + self.tracker.scan_interval_s
            if (
                self.tracker.scan_max_cycles > 0
                and self._boundary_hits >= self.tracker.scan_max_cycles * 2
            ):
                self.active = False
                self.finished = True
        return GimbalCommand(self._pan, self._tilt, applied=False, reason="search")

    def stop(self) -> None:
        self.active = False
        self.finished = False
