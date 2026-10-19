"""PCA9685 servo backend via Adafruit ServoKit (optional dependency)."""

from __future__ import annotations

import logging
from typing import Any

from avfm.actuation.base import Servo
from avfm.errors import DependencyMissingError

logger = logging.getLogger("avfm.actuation.pca9685")

_KIT_CACHE: dict[tuple[int, int], object] = {}


def clear_kit_cache() -> None:
    """Test hook; hardware stays untouched."""
    _KIT_CACHE.clear()


class PCA9685Servo(Servo):
    name = "pca9685"
    can_move = True
    physical = True

    def __init__(
        self,
        channel: int,
        *,
        name: str = "pca9685",
        angle_min: float = 0.0,
        angle_max: float = 180.0,
        address: int = 0x40,
        frequency: int = 50,
        min_pulse_us: int = 500,
        max_pulse_us: int = 2500,
        invert: bool = False,
    ) -> None:
        if not 0 <= channel <= 15:
            raise ValueError("PCA9685 channel must be in [0, 15]")
        if not angle_min < angle_max:
            raise ValueError("angle_min must be smaller than angle_max")
        if not 0 < min_pulse_us < max_pulse_us:
            raise ValueError("pulse widths must satisfy 0 < min < max")
        self.name = name
        self.channel = channel
        self._angle_min = angle_min
        self._angle_max = angle_max
        self._address = address
        self._frequency = frequency
        self._min_pulse_us = min_pulse_us
        self._max_pulse_us = max_pulse_us
        self._invert = invert
        self._angle = (angle_min + angle_max) / 2.0
        self._kit: Any = None
        self._servo: Any = None

    def _ensure(self) -> None:
        if self._servo is not None:
            return
        key = (self._address, self._frequency)
        kit = _KIT_CACHE.get(key)
        if kit is None:
            try:
                from adafruit_servokit import ServoKit
            except ImportError as exc:
                raise DependencyMissingError(
                    "adafruit-circuitpython-servokit is not installed. On Raspberry Pi run: "
                    "pip install -e '.[rpi]'  (or pip install adafruit-circuitpython-servokit)"
                ) from exc
            try:
                kit = ServoKit(channels=16, address=self._address)
                kit.frequency = self._frequency
                for index in range(16):
                    kit.servo[index].set_pulse_width_range(self._min_pulse_us, self._max_pulse_us)
                    kit.servo[index].actuation_range = 180
            except Exception as exc:
                raise DependencyMissingError(
                    f"PCA9685 not found at I2C address 0x{self._address:02X}. "
                    "Check wiring and run: sudo i2cdetect -y 1"
                ) from exc
            _KIT_CACHE[key] = kit
        self._kit = _KIT_CACHE[key]
        assert self._kit is not None
        self._servo = self._kit.servo[self.channel]
        # Apply this channel's pulse range even when the shared kit was created
        # by another servo with a different calibration.
        self._servo.set_pulse_width_range(self._min_pulse_us, self._max_pulse_us)
        self._servo.actuation_range = 180
        try:
            current = self._servo.angle
            if current is not None:
                self._angle = float(current)
        except Exception:  # pragma: no cover - hardware specific
            pass

    def initialize(self) -> None:
        """Force the I2C probe so ``auto`` can fall back before the loop starts."""
        self._ensure()

    def set_angle(self, angle: float) -> None:
        self._ensure()
        angle = max(self._angle_min, min(self._angle_max, float(angle)))
        assert self._servo is not None
        physical = 180.0 - angle if self._invert else angle
        self._servo.angle = physical
        self._angle = angle

    def get_angle(self) -> float:
        return self._angle

    def close(self) -> None:
        # The ServoKit is shared by all channels; do not deinit the board here.
        self._servo = None
        self._kit = None
