from __future__ import annotations

import sys
import types

import pytest

from avfm.actuation.base import ActuatorCapabilities, GimbalActuator
from avfm.actuation.factory import create_actuator
from avfm.actuation.mock import MockServo, NullServo
from avfm.actuation.pca9685 import PCA9685Servo, clear_kit_cache
from avfm.config import ActuatorConfig, AppConfig


def test_mock_and_null_servo() -> None:
    mock = MockServo(angle_min=0, angle_max=180)
    mock.set_angle(200)
    assert mock.get_angle() == 180
    assert mock.history == [180]
    null = NullServo(angle_min=0, angle_max=180)
    null.set_angle(45)
    assert null.get_angle() == 45
    assert null.can_move is False


def test_gimbal_actuator_applies_and_parks() -> None:
    config = AppConfig()
    pan = MockServo(angle_min=config.gimbal.pan_min, angle_max=config.gimbal.pan_max, can_move=True)
    tilt = MockServo(
        angle_min=config.gimbal.tilt_min, angle_max=config.gimbal.tilt_max, can_move=True
    )
    actuator = GimbalActuator(
        pan,
        tilt,
        config.gimbal,
        ActuatorCapabilities(True, False, "mock"),
        on_error="passive",
        park_pan=90,
        park_tilt=80,
    )
    from avfm.types import GimbalCommand

    assert actuator.apply(GimbalCommand(120, 90)) is True
    assert pan.get_angle() == 120
    assert actuator.park() is True
    assert pan.get_angle() == 90
    assert tilt.get_angle() == 80


def test_actuator_error_degrades() -> None:
    class BrokenServo(MockServo):
        def set_angle(self, angle: float) -> None:
            raise RuntimeError("I2C failure")

    config = AppConfig()
    pan = BrokenServo(
        angle_min=config.gimbal.pan_min, angle_max=config.gimbal.pan_max, can_move=True
    )
    tilt = MockServo(
        angle_min=config.gimbal.tilt_min, angle_max=config.gimbal.tilt_max, can_move=True
    )
    actuator = GimbalActuator(
        pan, tilt, config.gimbal, ActuatorCapabilities(True, True, "broken"), on_error="passive"
    )
    from avfm.types import GimbalCommand

    assert actuator.apply(GimbalCommand(120, 90)) is False
    assert actuator.degraded
    assert not actuator.can_move


def test_pca9685_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeServo:
        def __init__(self) -> None:
            self.angle = None
            self.pulse = None
            self.range = None

        def set_pulse_width_range(self, low: int, high: int) -> None:
            self.pulse = (low, high)

    class FakeKit:
        def __init__(self, channels: int, address: int) -> None:
            self.channels = channels
            self.address = address
            self.frequency = None
            self.servo = [FakeServo() for _ in range(16)]

    fake_module = types.ModuleType("adafruit_servokit")
    fake_module.ServoKit = FakeKit  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "adafruit_servokit", fake_module)
    clear_kit_cache()
    servo = PCA9685Servo(
        2,
        angle_min=40,
        angle_max=180,
        address=0x40,
        frequency=50,
        min_pulse_us=500,
        max_pulse_us=2500,
    )
    servo.initialize()
    assert servo.get_angle() == 110
    servo.set_angle(90)
    assert servo.get_angle() == 90
    clear_kit_cache()


def test_pca9685_reapplies_pulse_range_on_cached_kit(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeServo:
        def __init__(self) -> None:
            self.angle = None
            self.pulse = None
            self.range = None

        def set_pulse_width_range(self, low: int, high: int) -> None:
            self.pulse = (low, high)

    class FakeKit:
        instances: list[FakeKit] = []

        def __init__(self, channels: int, address: int) -> None:
            self.frequency = None
            self.servo = [FakeServo() for _ in range(16)]
            FakeKit.instances.append(self)

    fake_module = types.ModuleType("adafruit_servokit")
    fake_module.ServoKit = FakeKit  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "adafruit_servokit", fake_module)
    clear_kit_cache()
    first = PCA9685Servo(
        2,
        angle_min=40,
        angle_max=180,
        address=0x40,
        frequency=50,
        min_pulse_us=500,
        max_pulse_us=2500,
    )
    second = PCA9685Servo(
        3,
        angle_min=0,
        angle_max=140,
        address=0x40,
        frequency=50,
        min_pulse_us=600,
        max_pulse_us=2400,
    )
    first.initialize()
    second.initialize()
    assert FakeKit.instances[0].servo[2].pulse == (500, 2500)
    assert FakeKit.instances[0].servo[3].pulse == (600, 2400)
    clear_kit_cache()


def test_create_actuator_none_and_mock() -> None:
    config = AppConfig()
    none = create_actuator(config.actuator, config.gimbal)
    assert none.actual_backend == "none"
    assert not none.actuator.can_move
    mock_config = ActuatorConfig(backend="mock", assume_camera_moves=True)
    mock = create_actuator(mock_config, config.gimbal)
    assert mock.actual_backend == "mock"
    assert mock.actuator.can_move


def test_create_actuator_mock_parks_at_startup() -> None:
    config = AppConfig()
    mock_config = ActuatorConfig(backend="mock", assume_camera_moves=True)
    selection = create_actuator(
        mock_config,
        config.gimbal,
        park_angles=(90.0, 80.0),
    )
    assert selection.actuator.pan.get_angle() == 90.0
    assert selection.actuator.tilt.get_angle() == 80.0


def test_create_actuator_auto_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    config = AppConfig()
    auto_config = ActuatorConfig(backend="auto")

    def fail(*args, **kwargs):
        raise RuntimeError("no I2C")

    monkeypatch.setattr("avfm.actuation.factory._pca_pair", fail)
    selection = create_actuator(auto_config, config.gimbal)
    assert selection.actual_backend == "none"
    assert selection.fallback_reason
