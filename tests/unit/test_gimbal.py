from __future__ import annotations

import dataclasses

from avfm.config import AppConfig
from avfm.control.gimbal import GimbalController


def test_first_update_does_not_move() -> None:
    config = AppConfig()
    controller = GimbalController(config.tracker, config.gimbal)
    command = controller.update_errors(0.5, 0.5, now=0.0)
    assert command.pan == config.tracker.default_pan
    assert command.tilt == config.tracker.default_tilt


def test_second_update_moves_toward_error() -> None:
    config = AppConfig()
    controller = GimbalController(config.tracker, config.gimbal)
    controller.update_errors(0.5, 0.5, now=0.0)
    command = controller.update_errors(0.5, 0.5, now=0.1)
    assert command.pan > config.tracker.default_pan
    assert command.tilt > config.tracker.default_tilt
    assert abs(command.pan - config.tracker.default_pan) <= config.gimbal.max_step_deg


def test_invert_pan() -> None:
    config = AppConfig()
    tracker = dataclasses.replace(config.tracker, invert_pan=True)
    controller = GimbalController(tracker, config.gimbal)
    controller.update_errors(0.5, 0.0, now=0.0)
    command = controller.update_errors(0.5, 0.0, now=0.1)
    assert command.pan < config.tracker.default_pan


def test_limits_clamp() -> None:
    config = AppConfig()
    controller = GimbalController(config.tracker, config.gimbal)
    controller.set_current(config.gimbal.pan_max, config.gimbal.tilt_max)
    for index in range(30):
        command = controller.update_errors(1.0, 1.0, now=index * 0.1)
    assert command.pan <= config.gimbal.pan_max
    assert command.tilt <= config.gimbal.tilt_max


def test_update_bbox_sign() -> None:
    config = AppConfig()
    controller = GimbalController(config.tracker, config.gimbal)
    controller.update_errors(0.0, 0.0, now=0.0)
    from avfm.types import BBox

    command = controller.update_bbox(BBox(0.6, 0.3, 0.2, 0.2), (640, 480), now=0.1)
    assert command.pan > config.tracker.default_pan


def test_park_and_reset() -> None:
    config = AppConfig()
    controller = GimbalController(config.tracker, config.gimbal)
    controller.update_errors(0.5, 0.5, now=0.0)
    controller.update_errors(0.5, 0.5, now=0.1)
    command = controller.park(now=0.2)
    assert command.pan == config.tracker.default_pan
    assert command.tilt == config.tracker.default_tilt
    assert controller.pan_pid.integral == 0.0
