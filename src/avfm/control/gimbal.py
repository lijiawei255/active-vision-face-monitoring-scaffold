"""Pan/tilt controller built from two PID axes and mechanical limits."""

from __future__ import annotations

import dataclasses

from avfm.config import GimbalConfig, PIDConfig, TrackerConfig
from avfm.control.pid import PIDAxis
from avfm.types import BBox, GimbalCommand


class GimbalController:
    def __init__(self, tracker: TrackerConfig, gimbal: GimbalConfig) -> None:
        pan_cfg: PIDConfig = dataclasses.replace(tracker.pan_pid, deadband=tracker.deadband_x)
        tilt_cfg: PIDConfig = dataclasses.replace(tracker.tilt_pid, deadband=tracker.deadband_y)
        self.pan_pid = PIDAxis(pan_cfg)
        self.tilt_pid = PIDAxis(tilt_cfg)
        self.tracker = tracker
        self.gimbal = gimbal
        self.current_pan = tracker.default_pan
        self.current_tilt = tracker.default_tilt
        self._last_time: float | None = None

    def update_errors(self, ex: float, ey: float, now: float) -> GimbalCommand:
        dt = 0.0 if self._last_time is None else max(0.0, min(1.0, now - self._last_time))
        self._last_time = now

        pan_sign = -1.0 if self.tracker.invert_pan else 1.0
        tilt_sign = -1.0 if self.tracker.invert_tilt else 1.0
        pan_rate = pan_sign * self.pan_pid.update(ex, dt)
        tilt_rate = tilt_sign * self.tilt_pid.update(ey, dt)

        delta_pan = max(-self.gimbal.max_step_deg, min(self.gimbal.max_step_deg, pan_rate * dt))
        delta_tilt = max(-self.gimbal.max_step_deg, min(self.gimbal.max_step_deg, tilt_rate * dt))

        self.current_pan = max(
            self.gimbal.pan_min, min(self.gimbal.pan_max, self.current_pan + delta_pan)
        )
        self.current_tilt = max(
            self.gimbal.tilt_min, min(self.gimbal.tilt_max, self.current_tilt + delta_tilt)
        )
        return GimbalCommand(
            pan=self.current_pan,
            tilt=self.current_tilt,
            pan_rate=pan_rate,
            tilt_rate=tilt_rate,
            applied=False,
            reason="track",
        )

    def update_bbox(self, bbox: BBox, frame_size: tuple[int, int], now: float) -> GimbalCommand:
        # Normalised offsets: 0 at the frame centre, +1 at the right/bottom edge.
        ex = (bbox.cx - 0.5) * 2.0
        ey = (bbox.cy - 0.5) * 2.0
        return self.update_errors(ex, ey, now)

    def hold_command(self, reason: str = "hold") -> GimbalCommand:
        return GimbalCommand(
            pan=self.current_pan,
            tilt=self.current_tilt,
            applied=False,
            reason=reason,
        )

    def set_current(self, pan: float, tilt: float) -> None:
        self.current_pan = max(self.gimbal.pan_min, min(self.gimbal.pan_max, pan))
        self.current_tilt = max(self.gimbal.tilt_min, min(self.gimbal.tilt_max, tilt))

    def park(self, now: float | None = None) -> GimbalCommand:
        self.current_pan = self.tracker.default_pan
        self.current_tilt = self.tracker.default_tilt
        self.reset_pid()
        if now is not None:
            self._last_time = now
        return self.hold_command(reason="park")

    def reset_pid(self, now: float | None = None) -> None:
        self.pan_pid.reset()
        self.tilt_pid.reset()
        if now is not None:
            self._last_time = now
