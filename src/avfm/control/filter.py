"""EMA smoothing and short hold for detector observations."""

from __future__ import annotations

from avfm.types import BBox


class ObservationFilter:
    def __init__(self, alpha: float = 0.5, hold_last_s: float = 0.3) -> None:
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha must be in [0, 1]")
        self.alpha = alpha
        self.hold_last_s = max(0.0, hold_last_s)
        self._bbox: BBox | None = None
        self._last_seen: float | None = None

    def update(self, bbox: BBox | None, now: float) -> None:
        if bbox is None:
            return
        if self._bbox is None:
            self._bbox = bbox
        else:
            a = self.alpha
            self._bbox = BBox(
                self._bbox.x * (1 - a) + bbox.x * a,
                self._bbox.y * (1 - a) + bbox.y * a,
                self._bbox.w * (1 - a) + bbox.w * a,
                self._bbox.h * (1 - a) + bbox.h * a,
            ).clamp()
        self._last_seen = now

    def get(self, now: float) -> BBox | None:
        if self._bbox is None or self._last_seen is None:
            return None
        if now - self._last_seen > self.hold_last_s:
            return None
        return self._bbox

    @property
    def last_seen(self) -> float | None:
        return self._last_seen

    def reset(self) -> None:
        self._bbox = None
        self._last_seen = None
