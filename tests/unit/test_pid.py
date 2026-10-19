from __future__ import annotations

import pytest

from avfm.config import PIDConfig
from avfm.control.pid import PIDAxis


def make_pid(**kwargs) -> PIDAxis:
    defaults = {
        "kp": 10.0,
        "ki": 1.0,
        "kd": 0.1,
        "output_limit": 50.0,
        "integral_limit": 10.0,
        "deadband": 0.01,
        "integral_decay": 1.0,
    }
    defaults.update(kwargs)
    return PIDAxis(PIDConfig(**defaults))


def test_zero_dt_returns_zero() -> None:
    pid = make_pid()
    assert pid.update(0.5, 0.0) == 0.0
    assert pid.update(0.5, -0.1) == 0.0


def test_positive_error_positive_output() -> None:
    pid = make_pid()
    output = pid.update(0.5, 0.1)
    assert output > 0
    assert pid.last_output == output


def test_negative_error_negative_output() -> None:
    pid = make_pid()
    assert pid.update(-0.5, 0.1) < 0


def test_deadband_and_integral_leak() -> None:
    pid = make_pid(kp=10.0, ki=5.0, deadband=0.1)
    pid.update(0.5, 0.1)
    integral_before = pid.integral
    assert integral_before > 0
    assert pid.update(0.05, 0.1) == 0.0
    assert pid.integral < integral_before


def test_output_saturation_and_anti_windup() -> None:
    pid = make_pid(kp=1000.0, ki=100.0, output_limit=5.0, integral_limit=100.0)
    for _ in range(50):
        output = pid.update(1.0, 0.1)
    assert abs(output) <= 5.0
    assert abs(pid.integral) <= 100.0


def test_reset() -> None:
    pid = make_pid()
    pid.update(0.5, 0.1)
    pid.reset()
    assert pid.integral == 0.0
    assert pid.prev_error == 0.0
    assert pid.last_output == 0.0
    assert pid.initialized is False


@pytest.mark.parametrize("error", [0.2, -0.2, 0.7, -0.7])
def test_output_finite(error: float) -> None:
    pid = make_pid()
    output = pid.update(error, 1.0 / 15.0)
    assert output == pytest.approx(output)
    assert abs(output) <= 50.0
