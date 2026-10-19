from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from avfm.config import AppConfig, load_config
from avfm.errors import ConfigError

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_default_config_loads_code_defaults(tmp_path: Path) -> None:
    config = load_config(cwd=tmp_path)
    assert isinstance(config, AppConfig)
    assert config.detector.mode == "single"
    assert config.actuator.backend == "none"
    assert config.tracker.pan_pid.kp == 120.0


def test_rpi_profile_overrides(tmp_path: Path) -> None:
    config = load_config(profile="rpi", cwd=REPO_ROOT)
    assert config.detector.mode == "split"
    assert config.detector.tracking_backend == "yunet"
    assert config.detector.fatigue_backend == "mediapipe"
    assert config.camera.source == "picamera"
    assert config.camera.flip == "vertical"
    assert config.actuator.backend == "auto"


def test_invalid_override_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(cwd=tmp_path, overrides={"runtime.fps": 0.0})
    with pytest.raises(ConfigError):
        load_config(cwd=tmp_path, overrides={"camera.flip": "sideways"})
    with pytest.raises(ConfigError):
        load_config(cwd=tmp_path, overrides={"tracker.default_pan": 10.0})


def test_unknown_toml_key_raises(tmp_path: Path) -> None:
    profile = tmp_path / "configs" / "bad.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text("[runtime]\nunknown_key = 1\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(profile="bad", cwd=tmp_path)


def test_config_roundtrip_dict() -> None:
    config = AppConfig()
    data = config.to_dict()
    assert data["camera"]["width"] == 640
    assert data["tracker"]["pan_pid"]["kp"] == 120.0


def test_demo_profile_does_not_change_normal_profiles(tmp_path: Path) -> None:
    """Demo acceleration must stay in demo_short.toml, not the defaults."""
    code_defaults = load_config(cwd=tmp_path)
    desktop = load_config(profile="desktop", cwd=REPO_ROOT)
    demo = load_config(profile="demo_short", cwd=REPO_ROOT)

    assert code_defaults.fatigue.perclos_window_s == 60.0
    assert code_defaults.fatigue.perclos_warmup_s == 30.0
    assert code_defaults.fatigue.distraction_confirm_s == 2.0
    assert code_defaults.fatigue.distraction_pitch_deg == 15.0
    assert code_defaults.fatigue.ear_max_pitch_deg == 20.0

    assert desktop.fatigue.perclos_window_s == 60.0
    assert desktop.fatigue.perclos_warmup_s == 30.0
    assert desktop.fatigue.distraction_confirm_s == 2.0
    assert desktop.fatigue.recovery_s == 2.0
    assert desktop.fatigue.distraction_pitch_deg == 25.0

    assert demo.fatigue.perclos_window_s == 10.0
    assert demo.fatigue.perclos_warmup_s == 5.0
    assert demo.fatigue.distraction_confirm_s == 1.0
    assert demo.fatigue.recovery_s == 1.0
    assert demo.camera.fps == 12.7


def test_replace_validates_cross_fields() -> None:
    config = AppConfig()
    with pytest.raises(ConfigError):
        dataclasses.replace(config, tracker=dataclasses.replace(config.tracker, default_pan=10.0))
