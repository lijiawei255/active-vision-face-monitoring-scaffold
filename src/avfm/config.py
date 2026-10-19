"""Typed application configuration with TOML profiles and validation.

The code defaults are the canonical values. ``configs/default.toml`` mirrors
them for documentation and for users who prefer editing a file. Profiles
(``configs/rpi.toml`` etc.) contain only overrides and are deep-merged.
"""

from __future__ import annotations

import copy
import dataclasses
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_type_hints

from avfm.errors import ConfigError

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass
class RuntimeConfig:
    fps: float = 15.0
    show: bool = False
    log_level: str = "INFO"
    max_frame_age_s: float = 0.5
    report_metrics: bool = True

    def validate(self) -> None:
        if self.fps <= 0:
            raise ConfigError(f"runtime.fps must be > 0, got {self.fps}")
        if self.max_frame_age_s <= 0:
            raise ConfigError("runtime.max_frame_age_s must be > 0")
        if str(self.log_level).upper() not in _LOG_LEVELS:
            raise ConfigError(f"runtime.log_level must be one of {sorted(_LOG_LEVELS)}")


@dataclass
class CameraConfig:
    source: str = "webcam:0"
    width: int = 640
    height: int = 480
    fps: float = 15.0
    flip: str = "none"
    hfov_deg: float = 60.0
    warmup_s: float = 0.5

    def validate(self) -> None:
        if not self.source:
            raise ConfigError("camera.source must not be empty")
        if self.width <= 0 or self.height <= 0:
            raise ConfigError("camera.width/height must be > 0")
        if self.fps <= 0:
            raise ConfigError("camera.fps must be > 0")
        if self.flip not in {"none", "horizontal", "vertical", "both"}:
            raise ConfigError("camera.flip must be none|horizontal|vertical|both")
        if not 0 < self.hfov_deg < 180:
            raise ConfigError("camera.hfov_deg must be between 0 and 180")
        if self.warmup_s < 0:
            raise ConfigError("camera.warmup_s must be >= 0")


@dataclass
class DetectorConfig:
    mode: str = "single"
    backend: str = "auto"
    tracking_backend: str = "yunet"
    fatigue_backend: str = "mediapipe"
    interval_frames: int = 1
    tracking_interval_frames: int = 1
    fatigue_interval_frames: int = 2
    yunet_model: str = "models/yunet/face_detection_yunet_2026may.onnx"
    mediapipe_model: str = "models/mediapipe/face_landmarker.task"
    max_faces: int = 1
    score_threshold: float = 0.6
    nms_threshold: float = 0.3
    min_detection_confidence: float = 0.5
    min_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5

    def validate(self) -> None:
        if self.mode not in {"single", "split"}:
            raise ConfigError("detector.mode must be single or split")
        if self.backend not in {"auto", "yunet", "mediapipe"}:
            raise ConfigError("detector.backend must be auto|yunet|mediapipe")
        if self.tracking_backend not in {"auto", "yunet", "mediapipe"}:
            raise ConfigError("detector.tracking_backend must be auto|yunet|mediapipe")
        if self.fatigue_backend not in {"auto", "mediapipe", "none"}:
            raise ConfigError("detector.fatigue_backend must be auto|mediapipe|none")
        for name in (
            "interval_frames",
            "tracking_interval_frames",
            "fatigue_interval_frames",
        ):
            if getattr(self, name) < 1:
                raise ConfigError(f"detector.{name} must be >= 1")
        if self.max_faces < 1:
            raise ConfigError("detector.max_faces must be >= 1")
        for name in (
            "score_threshold",
            "nms_threshold",
            "min_detection_confidence",
            "min_presence_confidence",
            "min_tracking_confidence",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ConfigError(f"detector.{name} must be in [0, 1]")


@dataclass
class PIDConfig:
    kp: float = 120.0
    ki: float = 5.0
    kd: float = 1.2
    output_limit: float = 240.0
    integral_limit: float = 50.0
    deadband: float = 0.03
    integral_decay: float = 1.0

    def validate(self, name: str) -> None:
        if self.kp < 0 or self.ki < 0 or self.kd < 0:
            raise ConfigError(f"{name}.kp/ki/kd must be >= 0")
        if self.output_limit <= 0:
            raise ConfigError(f"{name}.output_limit must be > 0")
        if self.integral_limit < 0:
            raise ConfigError(f"{name}.integral_limit must be >= 0")
        if self.deadband < 0 or self.deadband > 1:
            raise ConfigError(f"{name}.deadband must be in [0, 1]")
        if self.integral_decay < 0:
            raise ConfigError(f"{name}.integral_decay must be >= 0")


@dataclass
class TrackerConfig:
    deadband_x: float = 0.03
    deadband_y: float = 0.03
    hold_last_s: float = 0.3
    lost_timeout_s: float = 10.0
    ema_alpha: float = 0.5
    default_pan: float = 90.0
    default_tilt: float = 80.0
    scan_step_deg: float = 5.0
    scan_interval_s: float = 0.2
    scan_tilt_deg: float = 80.0
    scan_max_cycles: int = 0
    invert_pan: bool = False
    invert_tilt: bool = False
    pan_pid: PIDConfig = field(default_factory=PIDConfig)
    tilt_pid: PIDConfig = field(
        default_factory=lambda: PIDConfig(
            kp=100.0, ki=5.0, kd=1.0, output_limit=200.0, deadband=0.03
        )
    )

    def validate(self) -> None:
        if not 0.0 <= self.deadband_x <= 1.0 or not 0.0 <= self.deadband_y <= 1.0:
            raise ConfigError("tracker.deadband_x/y must be in [0, 1]")
        if self.hold_last_s < 0 or self.lost_timeout_s < 0:
            raise ConfigError("tracker.hold_last_s/lost_timeout_s must be >= 0")
        if not 0.0 <= self.ema_alpha <= 1.0:
            raise ConfigError("tracker.ema_alpha must be in [0, 1]")
        if self.scan_step_deg <= 0 or self.scan_interval_s <= 0:
            raise ConfigError("tracker.scan_step_deg/scan_interval_s must be > 0")
        if self.scan_max_cycles < 0:
            raise ConfigError("tracker.scan_max_cycles must be >= 0")
        self.pan_pid.validate("tracker.pan_pid")
        self.tilt_pid.validate("tracker.tilt_pid")


@dataclass
class GimbalConfig:
    pan_min: float = 40.0
    pan_max: float = 180.0
    tilt_min: float = 0.0
    tilt_max: float = 140.0
    max_step_deg: float = 10.0
    command_deadband_deg: float = 0.2
    park_on_exit: bool = True

    def validate(self) -> None:
        if self.pan_min >= self.pan_max:
            raise ConfigError("gimbal.pan_min must be < pan_max")
        if self.tilt_min >= self.tilt_max:
            raise ConfigError("gimbal.tilt_min must be < tilt_max")
        if self.max_step_deg <= 0:
            raise ConfigError("gimbal.max_step_deg must be > 0")
        if self.command_deadband_deg < 0:
            raise ConfigError("gimbal.command_deadband_deg must be >= 0")


@dataclass
class FatigueConfig:
    enabled: bool = True
    ear_threshold: float = 0.2
    ear_calibration_file: str = ""
    closure_confirm_s: float = 0.3
    microsleep_s: float = 1.5
    blink_min_s: float = 0.05
    blink_max_s: float = 0.4
    perclos_window_s: float = 60.0
    perclos_threshold: float = 0.2
    perclos_min_coverage: float = 0.8
    perclos_warmup_s: float = 30.0
    perclos_max_gap_s: float = 0.5
    max_metrics_age_s: float = 0.5
    distraction_yaw_deg: float = 20.0
    distraction_pitch_deg: float = 15.0
    distraction_confirm_s: float = 2.0
    recovery_s: float = 2.0
    event_cooldown_s: float = 15.0
    face_lost_s: float = 1.0
    ear_max_yaw_deg: float = 25.0
    ear_max_pitch_deg: float = 20.0
    max_reproj_error_px: float = 20.0

    def validate(self) -> None:
        if not 0.0 <= self.ear_threshold <= 1.0:
            raise ConfigError("fatigue.ear_threshold must be in [0, 1]")
        if self.closure_confirm_s < 0:
            raise ConfigError("fatigue.closure_confirm_s must be >= 0")
        if self.microsleep_s <= 0:
            raise ConfigError("fatigue.microsleep_s must be > 0")
        if self.blink_min_s < 0 or self.blink_max_s < self.blink_min_s:
            raise ConfigError("fatigue.blink_min_s/blink_max_s are invalid")
        if self.blink_max_s >= self.microsleep_s:
            raise ConfigError("fatigue.blink_max_s must be < microsleep_s")
        if self.perclos_window_s <= 0:
            raise ConfigError("fatigue.perclos_window_s must be > 0")
        if not 0.0 <= self.perclos_threshold <= 1.0:
            raise ConfigError("fatigue.perclos_threshold must be in [0, 1]")
        if not 0.0 <= self.perclos_min_coverage <= 1.0:
            raise ConfigError("fatigue.perclos_min_coverage must be in [0, 1]")
        if self.perclos_warmup_s < 0 or self.perclos_warmup_s > self.perclos_window_s:
            raise ConfigError("fatigue.perclos_warmup_s must be in [0, window]")
        if self.perclos_max_gap_s <= 0 or self.max_metrics_age_s <= 0:
            raise ConfigError("fatigue.perclos_max_gap_s/max_metrics_age_s must be > 0")
        for name in (
            "distraction_yaw_deg",
            "distraction_pitch_deg",
            "ear_max_yaw_deg",
            "ear_max_pitch_deg",
        ):
            if getattr(self, name) < 0:
                raise ConfigError(f"fatigue.{name} must be >= 0")
        for name in (
            "distraction_confirm_s",
            "recovery_s",
            "event_cooldown_s",
            "face_lost_s",
            "max_reproj_error_px",
        ):
            if getattr(self, name) < 0:
                raise ConfigError(f"fatigue.{name} must be >= 0")


@dataclass
class ActuatorConfig:
    backend: str = "none"
    assume_camera_moves: bool = False
    on_error: str = "passive"
    pca9685_address: int = 0x40
    pca9685_frequency: int = 50
    pan_channel: int = 2
    tilt_channel: int = 3
    min_pulse_us: int = 500
    max_pulse_us: int = 2500

    def validate(self) -> None:
        if self.backend not in {"none", "mock", "pca9685", "auto"}:
            raise ConfigError("actuator.backend must be none|mock|pca9685|auto")
        if self.on_error not in {"passive", "stop", "raise"}:
            raise ConfigError("actuator.on_error must be passive|stop|raise")
        if not 0 <= self.pca9685_address <= 0x7F:
            raise ConfigError("actuator.pca9685_address must be a 7-bit I2C address")
        if self.pca9685_frequency <= 0:
            raise ConfigError("actuator.pca9685_frequency must be > 0")
        if not 0 <= self.pan_channel <= 15 or not 0 <= self.tilt_channel <= 15:
            raise ConfigError("actuator channels must be in [0, 15]")
        if not 0 < self.min_pulse_us < self.max_pulse_us:
            raise ConfigError("actuator pulse widths must satisfy 0 < min < max")


@dataclass
class AppConfig:
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    gimbal: GimbalConfig = field(default_factory=GimbalConfig)
    fatigue: FatigueConfig = field(default_factory=FatigueConfig)
    actuator: ActuatorConfig = field(default_factory=ActuatorConfig)
    loaded_from: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.runtime.validate()
        self.camera.validate()
        self.detector.validate()
        self.tracker.validate()
        self.gimbal.validate()
        self.fatigue.validate()
        self.actuator.validate()
        for name, value in (
            ("tracker.default_pan", self.tracker.default_pan),
            ("tracker.default_tilt", self.tracker.default_tilt),
            ("tracker.scan_tilt_deg", self.tracker.scan_tilt_deg),
        ):
            if name.endswith("pan") and not self.gimbal.pan_min <= value <= self.gimbal.pan_max:
                raise ConfigError(f"{name}={value} is outside gimbal pan limits")
            if (
                not name.endswith("pan")
                and not self.gimbal.tilt_min <= value <= self.gimbal.tilt_max
            ):
                raise ConfigError(f"{name}={value} is outside gimbal tilt limits")

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _load_dataclass(cls: type, data: dict[str, Any], path: str = "") -> Any:
    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for key, value in data.items():
        if key not in hints:
            raise ConfigError(f"Unknown configuration key: {path}{key}")
        field_type = hints[key]
        if dataclasses.is_dataclass(field_type):
            if not isinstance(value, dict):
                raise ConfigError(f"{path}{key} must be a table")
            kwargs[key] = _load_dataclass(field_type, value, f"{path}{key}.")
        else:
            kwargs[key] = value
    try:
        return cls(**kwargs)
    except ConfigError:
        raise
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid configuration at {path or '<root>'}: {exc}") from exc


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _set_dot(data: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    target = data
    for part in parts[:-1]:
        if part not in target or not isinstance(target[part], dict):
            target[part] = {}
        target = target[part]
    target[parts[-1]] = value


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Configuration root in {path} must be a table")
    return data


def load_config(
    config_path: str | Path | None = None,
    profile: str | None = None,
    overrides: dict[str, Any] | None = None,
    cwd: str | Path | None = None,
) -> AppConfig:
    """Load defaults, optional default/profile TOML, explicit TOML and overrides."""
    root = Path(cwd) if cwd is not None else Path.cwd()
    data = AppConfig().to_dict()
    paths: list[str] = []

    default_path = root / "configs" / "default.toml"
    if default_path.exists():
        _deep_merge(data, _read_toml(default_path))
        paths.append(str(default_path))

    if profile:
        profile_path = root / "configs" / f"{profile}.toml"
        if not profile_path.exists():
            available = (
                sorted(p.stem for p in (root / "configs").glob("*.toml"))
                if (root / "configs").exists()
                else []
            )
            raise ConfigError(f"Unknown profile '{profile}'. Available: {available}")
        _deep_merge(data, _read_toml(profile_path))
        paths.append(str(profile_path))

    env_path = os.environ.get("AVFM_CONFIG")
    explicit = config_path or env_path
    if explicit:
        explicit_path = Path(explicit)
        if not explicit_path.is_absolute():
            explicit_path = root / explicit_path
        _deep_merge(data, _read_toml(explicit_path))
        paths.append(str(explicit_path))

    for key, value in (overrides or {}).items():
        _set_dot(data, key, value)

    data["loaded_from"] = tuple(paths)
    return _load_dataclass(AppConfig, data)
