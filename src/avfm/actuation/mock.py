"""In-memory servo backends for tests, desktop demos and passive mode."""

from __future__ import annotations

from avfm.actuation.base import Servo


class NullServo(Servo):
    """Records the last commanded angle but never moves."""

    def __init__(
        self, name: str = "null", angle_min: float = 0.0, angle_max: float = 180.0
    ) -> None:
        self.name = name
        self.can_move = False
        self.physical = False
        self._angle_min = angle_min
        self._angle_max = angle_max
        self._angle = angle_min

    def set_angle(self, angle: float) -> None:
        self._angle = max(self._angle_min, min(self._angle_max, float(angle)))

    def get_angle(self) -> float:
        return self._angle

    def close(self) -> None:
        return None


class MockServo(Servo):
    """Records command history. Never sleeps, never touches hardware."""

    def __init__(
        self,
        name: str = "mock",
        angle_min: float = 0.0,
        angle_max: float = 180.0,
        *,
        can_move: bool = False,
    ) -> None:
        self.name = name
        self.can_move = bool(can_move)
        self.physical = False
        self._angle_min = angle_min
        self._angle_max = angle_max
        self._angle = (angle_min + angle_max) / 2.0
        self.history: list[float] = []

    def set_angle(self, angle: float) -> None:
        self._angle = max(self._angle_min, min(self._angle_max, float(angle)))
        self.history.append(self._angle)

    def get_angle(self) -> float:
        return self._angle

    def close(self) -> None:
        return None
