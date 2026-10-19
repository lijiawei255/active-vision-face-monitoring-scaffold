"""Actuator factory with explicit passive/auto fallback semantics."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from avfm.actuation.base import ActuatorCapabilities, GimbalActuator, Servo
from avfm.actuation.mock import MockServo, NullServo
from avfm.actuation.pca9685 import PCA9685Servo
from avfm.config import ActuatorConfig, GimbalConfig
from avfm.errors import ActuatorError

logger = logging.getLogger("avfm.actuation.factory")


@dataclass
class ActuatorSelection:
    actuator: GimbalActuator
    requested_backend: str
    actual_backend: str
    fallback_reason: str = ""

    @property
    def capabilities(self) -> ActuatorCapabilities:
        return self.actuator.capabilities

    @property
    def mode(self) -> str:
        if not self.actuator.capabilities.can_move:
            return "passive"
        return "active" if self.actuator.capabilities.physical else "virtual"


def _null_pair(gimbal: GimbalConfig, reason: str) -> tuple[Servo, Servo, ActuatorCapabilities]:
    pan = NullServo("pan", gimbal.pan_min, gimbal.pan_max)
    tilt = NullServo("tilt", gimbal.tilt_min, gimbal.tilt_max)
    return pan, tilt, ActuatorCapabilities(False, False, "none", reason)


def _mock_pair(
    gimbal: GimbalConfig, config: ActuatorConfig
) -> tuple[Servo, Servo, ActuatorCapabilities]:
    can_move = bool(config.assume_camera_moves)
    pan = MockServo("pan", gimbal.pan_min, gimbal.pan_max, can_move=can_move)
    tilt = MockServo("tilt", gimbal.tilt_min, gimbal.tilt_max, can_move=can_move)
    return pan, tilt, ActuatorCapabilities(can_move, False, "mock", "in-memory servo")


def _pca_pair(
    gimbal: GimbalConfig, config: ActuatorConfig
) -> tuple[Servo, Servo, ActuatorCapabilities]:
    pan = PCA9685Servo(
        config.pan_channel,
        name="pan",
        angle_min=gimbal.pan_min,
        angle_max=gimbal.pan_max,
        address=config.pca9685_address,
        frequency=config.pca9685_frequency,
        min_pulse_us=config.min_pulse_us,
        max_pulse_us=config.max_pulse_us,
    )
    tilt = PCA9685Servo(
        config.tilt_channel,
        name="tilt",
        angle_min=gimbal.tilt_min,
        angle_max=gimbal.tilt_max,
        address=config.pca9685_address,
        frequency=config.pca9685_frequency,
        min_pulse_us=config.min_pulse_us,
        max_pulse_us=config.max_pulse_us,
    )
    # Probe I2C now, not at the first frame, so auto can fall back cleanly.
    pan.initialize()
    tilt.initialize()
    return pan, tilt, ActuatorCapabilities(True, True, "pca9685", "")


def create_actuator(
    config: ActuatorConfig,
    gimbal: GimbalConfig,
    *,
    park_angles: tuple[float, float] | None = None,
) -> ActuatorSelection:
    requested = config.backend
    actual = requested
    fallback_reason = ""
    if requested == "none":
        pan, tilt, caps = _null_pair(gimbal, "passive mode requested")
    elif requested == "mock":
        pan, tilt, caps = _mock_pair(gimbal, config)
    elif requested == "pca9685":
        try:
            pan, tilt, caps = _pca_pair(gimbal, config)
        except Exception as exc:
            raise ActuatorError(
                f"PCA9685 backend could not be initialized: {exc}. "
                "Use --servo none for passive mode, or --servo auto for fallback."
            ) from exc
    elif requested == "auto":
        try:
            pan, tilt, caps = _pca_pair(gimbal, config)
            actual = "pca9685"
        except Exception as exc:
            logger.warning("PCA9685 auto-probe failed; falling back to passive mode: %s", exc)
            pan, tilt, caps = _null_pair(gimbal, f"auto fallback: {exc}")
            actual = "none"
            fallback_reason = str(exc)
    else:  # pragma: no cover - config validation catches this
        raise ActuatorError(f"Unknown actuator backend: {requested}")

    actuator = GimbalActuator(
        pan,
        tilt,
        gimbal,
        caps,
        on_error=config.on_error,
        park_pan=park_angles[0] if park_angles else None,
        park_tilt=park_angles[1] if park_angles else None,
    )
    return ActuatorSelection(
        actuator=actuator,
        requested_backend=requested,
        actual_backend=actual,
        fallback_reason=fallback_reason,
    )
