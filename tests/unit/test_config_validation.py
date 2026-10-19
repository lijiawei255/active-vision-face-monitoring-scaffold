"""Every configuration validation branch must raise ``ConfigError``.

``configs/default.toml`` documents the values, but the validation code is the
last line of defence against a malformed profile, so each guard is exercised
here explicitly instead of relying on incidental profile coverage.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from avfm.config import load_config
from avfm.errors import ConfigError


@pytest.mark.parametrize(
    "overrides",
    [
        # runtime
        {"runtime.fps": 0},
        {"runtime.max_frame_age_s": 0},
        {"runtime.log_level": "NOPE"},
        # camera
        {"camera.source": ""},
        {"camera.width": 0},
        {"camera.height": 0},
        {"camera.fps": 0},
        {"camera.flip": "sideways"},
        {"camera.hfov_deg": 0},
        {"camera.hfov_deg": 180},
        {"camera.warmup_s": -1},
        # detector
        {"detector.mode": "duo"},
        {"detector.backend": "haar"},
        {"detector.tracking_backend": "haar"},
        {"detector.fatigue_backend": "eyes"},
        {"detector.interval_frames": 0},
        {"detector.tracking_interval_frames": 0},
        {"detector.fatigue_interval_frames": 0},
        {"detector.max_faces": 0},
        {"detector.score_threshold": 2.0},
        {"detector.nms_threshold": -0.1},
        {"detector.min_detection_confidence": 2.0},
        {"detector.min_presence_confidence": -1.0},
        {"detector.min_tracking_confidence": 2.0},
        # tracker PID
        {"tracker.pan_pid.kp": -1},
        {"tracker.pan_pid.ki": -1},
        {"tracker.tilt_pid.kd": -1},
        {"tracker.pan_pid.output_limit": 0},
        {"tracker.tilt_pid.integral_limit": -1},
        {"tracker.pan_pid.deadband": 2.0},
        {"tracker.tilt_pid.integral_decay": -1},
        # tracker
        {"tracker.deadband_x": 1.5},
        {"tracker.deadband_y": -0.5},
        {"tracker.hold_last_s": -1},
        {"tracker.lost_timeout_s": -1},
        {"tracker.ema_alpha": 2.0},
        {"tracker.scan_step_deg": 0},
        {"tracker.scan_interval_s": 0},
        {"tracker.scan_max_cycles": -1},
        # gimbal
        {"gimbal.pan_min": 200},
        {"gimbal.tilt_min": 200},
        {"gimbal.max_step_deg": 0},
        {"gimbal.command_deadband_deg": -1},
        # fatigue
        {"fatigue.ear_threshold": 2.0},
        {"fatigue.closure_confirm_s": -1},
        {"fatigue.microsleep_s": 0},
        {"fatigue.blink_min_s": -1},
        {"fatigue.blink_max_s": 0.01},
        {"fatigue.blink_max_s": 2.0},
        {"fatigue.perclos_window_s": 0},
        {"fatigue.perclos_threshold": 2.0},
        {"fatigue.perclos_min_coverage": 2.0},
        {"fatigue.perclos_warmup_s": 61},
        {"fatigue.perclos_max_gap_s": 0},
        {"fatigue.max_metrics_age_s": 0},
        {"fatigue.distraction_yaw_deg": -1},
        {"fatigue.distraction_pitch_deg": -1},
        {"fatigue.ear_max_yaw_deg": -1},
        {"fatigue.ear_max_pitch_deg": -1},
        {"fatigue.distraction_confirm_s": -1},
        {"fatigue.recovery_s": -1},
        {"fatigue.event_cooldown_s": -1},
        {"fatigue.face_lost_s": -1},
        {"fatigue.max_reproj_error_px": -1},
        # actuator
        {"actuator.backend": "servo"},
        {"actuator.on_error": "explode"},
        {"actuator.pca9685_address": 200},
        {"actuator.pca9685_frequency": 0},
        {"actuator.pan_channel": 16},
        {"actuator.tilt_channel": -1},
        {"actuator.min_pulse_us": 0},
        {"actuator.max_pulse_us": 100},
        # cross-field: tracker pose must sit inside the gimbal limits
        {"tracker.default_pan": 300},
        {"tracker.default_tilt": 300},
        {"tracker.scan_tilt_deg": -10},
    ],
)
def test_invalid_override_raises_config_error(tmp_path: Path, overrides: dict) -> None:
    with pytest.raises(ConfigError):
        load_config(cwd=tmp_path, overrides=overrides)


def test_non_numeric_override_is_wrapped_in_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(cwd=tmp_path, overrides={"camera.width": "wide"})


def test_nested_table_must_be_a_dict(tmp_path: Path) -> None:
    profile = tmp_path / "configs" / "bad.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text("camera = 5\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(profile="bad", cwd=tmp_path)


def test_unknown_profile_lists_available(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_config(profile="nope", cwd=tmp_path)
    assert "Unknown profile" in str(excinfo.value)


def test_unknown_profile_with_existing_profiles(tmp_path: Path) -> None:
    # Covers the "available profiles" formatting branch of the same error.
    profiles = tmp_path / "configs"
    profiles.mkdir(parents=True)
    (profiles / "alpha.toml").write_text("[runtime]\nfps = 10.0\n", encoding="utf-8")
    with pytest.raises(ConfigError) as excinfo:
        load_config(profile="missing", cwd=tmp_path)
    assert "alpha" in str(excinfo.value)


def test_explicit_config_path_is_loaded(tmp_path: Path) -> None:
    config_file = tmp_path / "explicit.toml"
    config_file.write_text("[camera]\nwidth = 320\n", encoding="utf-8")
    config = load_config(config_path=config_file, cwd=tmp_path)
    assert config.camera.width == 320
    assert str(config_file) in config.loaded_from


def test_avfm_config_env_var_is_loaded(tmp_path: Path) -> None:
    config_file = tmp_path / "from-env.toml"
    config_file.write_text("[camera]\nheight = 240\n", encoding="utf-8")
    environ = {"AVFM_CONFIG": str(config_file)}
    original = os.environ.get("AVFM_CONFIG")
    os.environ["AVFM_CONFIG"] = environ["AVFM_CONFIG"]
    try:
        config = load_config(cwd=tmp_path)
    finally:
        if original is None:
            os.environ.pop("AVFM_CONFIG", None)
        else:
            os.environ["AVFM_CONFIG"] = original
    assert config.camera.height == 240


def test_missing_explicit_config_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(config_path=tmp_path / "nope.toml", cwd=tmp_path)


def test_invalid_toml_raises(tmp_path: Path) -> None:
    config_file = tmp_path / "broken.toml"
    config_file.write_text("[camera\nwidth = 320\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(config_path=config_file, cwd=tmp_path)


def test_override_creates_deep_tables(tmp_path: Path) -> None:
    # Unknown nested keys must still produce a ConfigError, which proves the
    # dotted-override helper created the intermediate table first.
    with pytest.raises(ConfigError) as excinfo:
        load_config(cwd=tmp_path, overrides={"tracker.unknown_section.value": 1})
    assert "unknown_section" in str(excinfo.value)
