"""Face tracker state machine: track, hold, lose, search, reacquire."""

from __future__ import annotations

from avfm.config import GimbalConfig, TrackerConfig
from avfm.control.filter import ObservationFilter
from avfm.control.gimbal import GimbalController
from avfm.control.search import SearchController
from avfm.events import EventBus
from avfm.types import (
    Event,
    EventType,
    FaceObservation,
    GimbalCommand,
    TrackerResult,
    TrackerState,
)


class FaceTracker:
    def __init__(
        self,
        tracker: TrackerConfig,
        gimbal: GimbalConfig,
        *,
        can_actuate: bool = True,
        event_bus: EventBus | None = None,
    ) -> None:
        self.tracker = tracker
        self.gimbal_cfg = gimbal
        self.can_actuate = bool(can_actuate)
        self.event_bus = event_bus
        self.gimbal = GimbalController(tracker, gimbal)
        self.filter = ObservationFilter(tracker.ema_alpha, tracker.hold_last_s)
        self.search = SearchController(tracker, gimbal)
        self.state = TrackerState.IDLE
        self._last_seen: float | None = None
        self._last_frame_size: tuple[int, int] | None = None

    def _emit(
        self, event_type: EventType, timestamp: float, payload: dict | None = None
    ) -> Event | None:
        if self.event_bus is None:
            return None
        return self.event_bus.emit(event_type, timestamp, payload)

    def set_can_actuate(self, value: bool) -> None:
        self.can_actuate = bool(value)
        if not self.can_actuate and self.state == TrackerState.SEARCHING:
            self.search.stop()
            self.state = TrackerState.FACE_LOST

    def update(self, observation: FaceObservation | None, now: float) -> TrackerResult:
        events: list[Event] = []
        if observation is not None:
            self.filter.update(observation.bbox, now)
            self._last_seen = now
            self._last_frame_size = observation.frame_size
            was_lost = self.state != TrackerState.TRACKING
            if was_lost:
                self.search.stop()
                self.gimbal.reset_pid(now)
                event = self._emit(EventType.FACE_ACQUIRED, now, {})
                if event is not None:
                    events.append(event)
            self.state = TrackerState.TRACKING
            command = self.gimbal.update_bbox(observation.bbox, observation.frame_size, now)
            return TrackerResult(
                state=self.state,
                command=command,
                bbox=observation.bbox,
                events=tuple(events),
            )

        self.filter.update(None, now)
        held = self.filter.get(now)
        if held is not None and self._last_frame_size is not None:
            self.state = TrackerState.TRACKING
            command = self.gimbal.update_bbox(held, self._last_frame_size, now)
            return TrackerResult(
                state=self.state,
                command=command,
                bbox=held,
                events=tuple(events),
            )

        if self.state not in {TrackerState.FACE_LOST, TrackerState.SEARCHING}:
            self.state = TrackerState.FACE_LOST
            self.gimbal.reset_pid()
            if self._last_seen is not None:
                event = self._emit(EventType.FACE_LOST, now, {})
                if event is not None:
                    events.append(event)

        lost_long_enough = (
            self._last_seen is not None and now - self._last_seen >= self.tracker.lost_timeout_s
        )
        if self.can_actuate and lost_long_enough:
            if not self.search.active and not self.search.finished:
                self.search.start(now, self.gimbal.current_pan, self.gimbal.current_tilt)
                self.state = TrackerState.SEARCHING
                event = self._emit(EventType.SEARCH_STARTED, now, {})
                if event is not None:
                    events.append(event)
            if self.state == TrackerState.SEARCHING:
                command = self.search.step(now)
                self.gimbal.set_current(command.pan, command.tilt)
                if self.search.finished:
                    self.gimbal.reset_pid()
                    self.state = TrackerState.IDLE
                    event = self._emit(EventType.SEARCH_STOPPED, now, {"reason": "max_cycles"})
                    if event is not None:
                        events.append(event)
                    command = self.gimbal.park(now)
                return TrackerResult(
                    state=self.state,
                    command=command,
                    bbox=None,
                    events=tuple(events),
                )

        return TrackerResult(
            state=self.state,
            command=self.gimbal.hold_command("hold"),
            bbox=None,
            events=tuple(events),
        )

    def park(self, now: float | None = None) -> GimbalCommand:
        self.search.stop()
        self.state = TrackerState.IDLE
        self.filter.reset()
        self._last_seen = None
        return self.gimbal.park(now)
