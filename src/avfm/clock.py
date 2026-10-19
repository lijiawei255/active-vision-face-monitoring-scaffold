"""Clock abstraction so loops can be tested without real sleeping."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float:  # pragma: no cover - protocol
        ...

    def sleep(self, seconds: float) -> None:  # pragma: no cover - protocol
        ...


class MonotonicClock:
    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


class FakeClock:
    """Deterministic clock; ``sleep`` advances the virtual time."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = float(start)
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("sleep() requires a non-negative duration")
        self.sleeps.append(seconds)
        self._now += seconds

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("advance() requires a non-negative duration")
        self._now += seconds
