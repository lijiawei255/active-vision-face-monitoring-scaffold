"""Event sinks and a small fault-tolerant event bus."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

from avfm.types import Event, EventType

logger = logging.getLogger("avfm.events")


class EventSink(Protocol):
    def emit(self, event: Event) -> None:  # pragma: no cover - protocol
        ...


class NullEventSink:
    def emit(self, event: Event) -> None:
        return None


class ListEventSink:
    """Collect events for tests and in-process consumers."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def emit(self, event: Event) -> None:
        self.events.append(event)


class CallbackEventSink:
    def __init__(self, callback: Callable[[Event], None]) -> None:
        self._callback = callback

    def emit(self, event: Event) -> None:
        self._callback(event)


class EventBus:
    """Fan out events. A broken sink must not break the control loop."""

    def __init__(self, sinks: list[EventSink] | None = None) -> None:
        self._sinks: list[EventSink] = list(sinks or [])

    def add(self, sink: EventSink) -> None:
        self._sinks.append(sink)

    def emit(self, event_type: EventType, timestamp: float, payload: dict | None = None) -> Event:
        event = Event(type=event_type, timestamp=timestamp, payload=dict(payload or {}))
        for sink in tuple(self._sinks):
            try:
                sink.emit(event)
            except Exception:  # pragma: no cover - defensive
                logger.exception("event sink failed")
        return event
