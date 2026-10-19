"""Rolling PERCLOS window with coverage and freshness checks."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PerclosSample:
    timestamp: float
    closed: bool
    valid: bool


class PerclosWindow:
    """Time-based percentage of eye closure over a rolling window.

    ``PERCLOS`` here is the fraction of *valid* samples whose EAR was below
    the closure threshold. Invalid samples (no face, no landmarks, pose
    gating) are stored as ``valid=False`` so coverage reflects missing data.
    """

    def __init__(
        self,
        window_s: float = 60.0,
        *,
        min_coverage: float = 0.8,
        warmup_s: float = 30.0,
        max_gap_s: float = 0.5,
        min_samples: int = 10,
    ) -> None:
        if window_s <= 0:
            raise ValueError("window_s must be positive")
        if not 0 <= min_coverage <= 1:
            raise ValueError("min_coverage must be in [0, 1]")
        if warmup_s < 0 or warmup_s > window_s:
            raise ValueError("warmup_s must be in [0, window_s]")
        if max_gap_s <= 0:
            raise ValueError("max_gap_s must be positive")
        self.window_s = window_s
        self.min_coverage = min_coverage
        self.warmup_s = warmup_s
        self.max_gap_s = max_gap_s
        self.min_samples = min_samples
        self._samples: deque[PerclosSample] = deque()
        self._closed = 0
        self._valid = 0

    def _evict(self, now: float) -> None:
        cutoff = now - self.window_s
        while self._samples and self._samples[0].timestamp < cutoff:
            sample = self._samples.popleft()
            if sample.valid:
                self._valid -= 1
                if sample.closed:
                    self._closed -= 1

    def add(self, timestamp: float, closed: bool, valid: bool) -> None:
        sample = PerclosSample(
            timestamp=timestamp, closed=bool(closed and valid), valid=bool(valid)
        )
        self._samples.append(sample)
        if sample.valid:
            self._valid += 1
            if sample.closed:
                self._closed += 1
        self._evict(timestamp)

    def value(self, now: float) -> float:
        self._evict(now)
        if self._valid <= 0:
            return 0.0
        return self._closed / self._valid

    def coverage(self, now: float) -> float:
        self._evict(now)
        total = len(self._samples)
        if total <= 0:
            return 0.0
        return self._valid / total

    def ready(self, now: float) -> bool:
        self._evict(now)
        if not self._samples or self._valid < self.min_samples:
            return False
        first = self._samples[0]
        last = self._samples[-1]
        if now - first.timestamp < self.warmup_s:
            return False
        if now - last.timestamp > self.max_gap_s:
            return False
        return self.coverage(now) >= self.min_coverage

    def total_samples(self) -> int:
        return len(self._samples)

    def reset(self) -> None:
        self._samples.clear()
        self._closed = 0
        self._valid = 0
