"""Servo protocol and gimbal actuator wrapper."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from avfm.config import GimbalConfig
from avfm.errors import ActuatorError
from avfm.types import GimbalCommand

logger = logging.getLogger("avfm.actuation")


class Servo(ABC):
    name: str = "servo"
    can_move: bool = False
    physical: bool = False

    @abstractmethod
    def set_angle(self, angle: float) -> None: ...

    @abstractmethod
    def get_angle(self) -> float: ...

    @abstractmethod
    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ActuatorCapabilities:
    can_move: bool
    physical: bool
    name: str
    reason: str = ""


class GimbalActuator:
    """Apply pan/tilt commands to a pair of servos.

    ``on_error="passive"`` degrades to passive mode on a hardware failure;
    ``"stop"`` requests pipeline stop; ``"raise"`` re-raises.
    """

    def __init__(
        self,
        pan: Servo,
        tilt: Servo,
        gimbal: GimbalConfig,
        capabilities: ActuatorCapabilities,
        *,
        on_error: str = "passive",
        park_pan: float | None = None,
        park_tilt: float | None = None,
    ) -> None:
        if on_error not in {"passive", "stop", "raise"}:
            raise ValueError("on_error must be passive|stop|raise")
        self.pan = pan
        self.tilt = tilt
        self.gimbal = gimbal
        self.capabilities = capabilities
        self.on_error = on_error
        self.park_pan = (
            park_pan if park_pan is not None else (gimbal.pan_min + gimbal.pan_max) / 2.0
        )
        self.park_tilt = (
            park_tilt if park_tilt is not None else (gimbal.tilt_min + gimbal.tilt_max) / 2.0
        )
        self.degraded = False
        self.stop_requested = False
        self.last_error: Exception | None = None
        self.last_command: GimbalCommand | None = None

    @property
    def can_move(self) -> bool:
        return self.capabilities.can_move and not self.degraded

    def _handle_error(self, exc: Exception) -> bool:
        self.last_error = exc
        self.degraded = True
        logger.exception("actuator failure: %s", exc)
        if self.on_error == "raise":
            raise ActuatorError(f"Actuator failure: {exc}") from exc
        if self.on_error == "stop":
            self.stop_requested = True
        return False

    def apply(self, command: GimbalCommand) -> bool:
        self.last_command = command
        if not self.can_move:
            return False
        pan = max(self.gimbal.pan_min, min(self.gimbal.pan_max, command.pan))
        tilt = max(self.gimbal.tilt_min, min(self.gimbal.tilt_max, command.tilt))
        if (
            abs(pan - self.pan.get_angle()) < self.gimbal.command_deadband_deg
            and abs(tilt - self.tilt.get_angle()) < self.gimbal.command_deadband_deg
        ):
            return False
        try:
            self.pan.set_angle(pan)
            self.tilt.set_angle(tilt)
        except Exception as exc:  # hardware errors are contained
            return self._handle_error(exc)
        return True

    def park(self) -> bool:
        if not self.can_move:
            return False
        try:
            self.pan.set_angle(self.park_pan)
            self.tilt.set_angle(self.park_tilt)
        except Exception as exc:
            return self._handle_error(exc)
        return True

    def close(self) -> None:
        try:
            if self.gimbal.park_on_exit:
                self.park()
        finally:
            self.pan.close()
            self.tilt.close()
