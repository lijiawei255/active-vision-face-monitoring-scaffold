"""Fatigue state machine: EAR, blink/microsleep, PERCLOS and head pose."""

from __future__ import annotations

import logging
import math
from collections import deque

from avfm.config import FatigueConfig
from avfm.events import EventBus
from avfm.fatigue.calibration import EarCalibration
from avfm.fatigue.perclos import PerclosWindow
from avfm.types import Event, EventType, FaceMetrics, FatigueSnapshot, FatigueState

logger = logging.getLogger("avfm.fatigue")


class FatigueMonitor:
    """Turn per-observation metrics into drowsiness/distraction events.

    The monitor is deliberately heuristic. It is not a medical device and is
    not a certified driver-monitoring system.
    """

    def __init__(
        self,
        config: FatigueConfig,
        *,
        event_bus: EventBus | None = None,
        calibration: EarCalibration | None = None,
        available: bool = True,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.available = bool(available and config.enabled)
        self.ear_threshold = (
            calibration.threshold if calibration is not None else config.ear_threshold
        )
        self.calibration = calibration
        self._perclos = PerclosWindow(
            config.perclos_window_s,
            min_coverage=config.perclos_min_coverage,
            warmup_s=config.perclos_warmup_s,
            max_gap_s=config.perclos_max_gap_s,
        )
        self._closed_since: float | None = None
        self._open_since: float | None = None
        self._last_face_ts: float | None = None
        self._last_metrics_ts: float | None = None
        self._look_away_since: float | None = None
        self._look_ok_since: float | None = None
        self._drowsy = False
        self._distracted = False
        self._last_drowsy_event = -math.inf
        self._last_distracted_event = -math.inf
        self._blink_times: deque[float] = deque()

    # ------------------------------------------------------------------ utils
    def _emit(
        self, event_type: EventType, timestamp: float, payload: dict | None = None
    ) -> Event | None:
        if self.event_bus is None:
            return None
        return self.event_bus.emit(event_type, timestamp, payload)

    def _blink_rate(self, now: float) -> float:
        cutoff = now - 60.0
        while self._blink_times and self._blink_times[0] < cutoff:
            self._blink_times.popleft()
        return float(len(self._blink_times))

    def _ear_gated(self, metrics: FaceMetrics) -> bool:
        if not metrics.valid_pose:
            return False
        return (
            abs(metrics.yaw) > self.config.ear_max_yaw_deg
            or abs(metrics.pitch) > self.config.ear_max_pitch_deg
        )

    def _pose_looking_away(self, metrics: FaceMetrics) -> bool:
        if not metrics.valid_pose:
            return False
        return (
            abs(metrics.yaw) > self.config.distraction_yaw_deg
            or abs(metrics.pitch) > self.config.distraction_pitch_deg
        )

    # ----------------------------------------------------------------- update
    def update(
        self,
        metrics: FaceMetrics | None,
        timestamp: float,
        *,
        detection_ran: bool = True,
    ) -> FatigueSnapshot:
        events: list[Event] = []
        if not self.available:
            return FatigueSnapshot(
                state=FatigueState.UNAVAILABLE,
                reason="fatigue detector unavailable or disabled",
                timestamp=timestamp,  # type: ignore[call-arg]
            )

        fresh = (
            metrics is not None
            and metrics.valid_landmarks
            and timestamp - metrics.timestamp <= self.config.max_metrics_age_s
        )
        if metrics is not None and metrics.valid_landmarks:
            self._last_metrics_ts = metrics.timestamp
        ear_usable = fresh and not self._ear_gated(metrics)  # type: ignore[arg-type]

        # PERCLOS sampling only happens when the fatigue detector actually ran.
        if detection_ran:
            if ear_usable:
                closed = metrics.ear < self.ear_threshold  # type: ignore[union-attr]
                self._perclos.add(timestamp, closed=closed, valid=True)
            else:
                self._perclos.add(timestamp, closed=False, valid=False)

        # A face can be visible while the head is turned too far for a reliable
        # EAR; in that case it is still a face, just not an EAR sample.
        face_visible = fresh
        if face_visible:
            self._last_face_ts = timestamp

        # Closure / blink / microsleep bookkeeping.
        if ear_usable:
            closed = metrics.ear < self.ear_threshold  # type: ignore[union-attr]
            if closed:
                if self._closed_since is None:
                    self._closed_since = timestamp
                self._open_since = None
            else:
                if self._closed_since is not None:
                    duration = timestamp - self._closed_since
                    if self.config.blink_min_s <= duration <= self.config.blink_max_s:
                        self._blink_times.append(timestamp)
                        event = self._emit(EventType.BLINK, timestamp, {"duration_s": duration})
                        if event is not None:
                            events.append(event)
                    self._closed_since = None
                if self._open_since is None:
                    self._open_since = timestamp
        else:
            self._closed_since = None
            self._open_since = None

        # Drowsiness condition.
        microsleep = (
            self._closed_since is not None
            and timestamp - self._closed_since >= self.config.microsleep_s
        )
        perclos_ready = self._perclos.ready(timestamp)
        perclos = self._perclos.value(timestamp)
        perclos_high = perclos_ready and perclos >= self.config.perclos_threshold
        drowsy_now = bool(microsleep or perclos_high)

        if drowsy_now:
            if not self._drowsy:
                self._drowsy = True
                if timestamp - self._last_drowsy_event >= self.config.event_cooldown_s:
                    self._last_drowsy_event = timestamp
                    event = self._emit(
                        EventType.DROWSY_STARTED,
                        timestamp,
                        {"reason": "microsleep" if microsleep else "perclos", "perclos": perclos},
                    )
                    if event is not None:
                        events.append(event)
        elif self._drowsy and (
            self._open_since is not None and timestamp - self._open_since >= self.config.recovery_s
        ):
            self._drowsy = False
            event = self._emit(EventType.DROWSY_ENDED, timestamp, {})
            if event is not None:
                events.append(event)

        # Distraction condition (only when pose is valid).
        looking_away = self._pose_looking_away(metrics) if fresh else False
        if looking_away:
            self._look_ok_since = None
            if self._look_away_since is None:
                self._look_away_since = timestamp
            if (
                self._look_away_since is not None
                and timestamp - self._look_away_since >= self.config.distraction_confirm_s
                and not self._distracted
            ):
                self._distracted = True
                if timestamp - self._last_distracted_event >= self.config.event_cooldown_s:
                    self._last_distracted_event = timestamp
                    event = self._emit(
                        EventType.DISTRACTED_STARTED,
                        timestamp,
                        {"reason": "looking_away", "yaw": metrics.yaw, "pitch": metrics.pitch},  # type: ignore[union-attr]
                    )
                    if event is not None:
                        events.append(event)
        elif fresh and metrics is not None and metrics.valid_pose:
            self._look_away_since = None
            if self._distracted:
                if self._look_ok_since is None:
                    self._look_ok_since = timestamp
                if (
                    self._look_ok_since is not None
                    and timestamp - self._look_ok_since >= self.config.recovery_s
                ):
                    self._distracted = False
                    event = self._emit(EventType.DISTRACTED_ENDED, timestamp, {})
                    if event is not None:
                        events.append(event)

        # Determine observable state.
        no_face = (
            self._last_face_ts is None or timestamp - self._last_face_ts >= self.config.face_lost_s
        )
        if no_face:
            state = FatigueState.NO_FACE
        elif self._drowsy:
            state = FatigueState.DROWSY
        elif self._distracted:
            state = FatigueState.DISTRACTED
        else:
            state = FatigueState.ALERT

        if not fresh:
            ear = 0.0
            yaw = pitch = roll = 0.0
            eyes_closed = False
            looking_away = False
        else:
            assert metrics is not None
            ear = metrics.ear if ear_usable else 0.0
            yaw, pitch, roll = metrics.yaw, metrics.pitch, metrics.roll
            eyes_closed = bool(
                ear_usable
                and self._closed_since is not None
                and timestamp - self._closed_since >= self.config.closure_confirm_s
            )

        reason = ""
        if state == FatigueState.DROWSY:
            reason = "microsleep" if microsleep else "perclos"
        elif state == FatigueState.DISTRACTED:
            reason = "looking_away"
        elif state == FatigueState.NO_FACE:
            reason = "no_face"

        return FatigueSnapshot(
            state=state,
            timestamp=timestamp,
            ear=ear,
            perclos=perclos,
            perclos_ready=perclos_ready,
            coverage=self._perclos.coverage(timestamp),
            eyes_closed=eyes_closed,
            looking_away=looking_away,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            blink_rate=self._blink_rate(timestamp),
            reason=reason,
            events=tuple(events),
        )

    def reset(self) -> None:
        self._perclos.reset()
        self._closed_since = None
        self._open_since = None
        self._last_face_ts = None
        self._last_metrics_ts = None
        self._look_away_since = None
        self._look_ok_since = None
        self._drowsy = False
        self._distracted = False
        self._blink_times.clear()
