"""Environment and hardware capability reporting."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import platform
import sys
from dataclasses import dataclass

import cv2
import numpy as np

from avfm import __version__
from avfm.config import AppConfig
from avfm.detection.factory import mediapipe_available, model_ready
from avfm.models import MEDIAPIPE, YUNET, model_root, resolve_model_path


@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    available: bool
    detail: str
    hint: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "available": self.available,
            "detail": self.detail,
            "hint": self.hint,
        }


def _version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def probe_camera(max_index: int = 3) -> Capability:
    for index in range(max_index):
        cap = cv2.VideoCapture(index)
        try:
            if not cap.isOpened():
                continue
            ok, frame = cap.read()
            if ok and frame is not None:
                return Capability(
                    "camera",
                    True,
                    f"probe: /dev/video{index} or camera {index} returned {frame.shape[1]}x{frame.shape[0]}",
                )
        finally:
            cap.release()
    return Capability(
        "camera",
        False,
        "no camera responded to index 0..2",
        "On Windows check Camera privacy settings; on Pi run libcamera-hello --list-cameras.",
    )


def collect_capabilities(
    config: AppConfig | None = None,
    *,
    probe_camera_device: bool = False,
    probe_actuator: bool = False,
) -> list[Capability]:
    root = model_root()
    yunet_config = config.detector.yunet_model if config else None
    mp_config = config.detector.mediapipe_model if config else None
    yunet_path = resolve_model_path(YUNET, yunet_config, root)
    mp_path = resolve_model_path(MEDIAPIPE, mp_config, root)
    yunet_ok = model_ready(YUNET, yunet_config, root)
    mp_model_ok = model_ready(MEDIAPIPE, mp_config, root)
    mp_pkg = mediapipe_available()
    capabilities = [
        Capability("python", True, f"{sys.version.split()[0]} ({platform.platform()})"),
        Capability("avfm", True, __version__),
        Capability("numpy", True, np.__version__),
        Capability("opencv", hasattr(cv2, "FaceDetectorYN"), cv2.__version__),
        Capability(
            "mediapipe",
            mp_pkg,
            f"installed ({_version('mediapipe')})" if mp_pkg else "not installed",
            "pip install -e '.[mediapipe]'",
        ),
        Capability(
            "yunet_model",
            yunet_ok,
            str(yunet_path) if yunet_ok else f"missing: {yunet_path}",
            "avfm models download --only yunet",
        ),
        Capability(
            "mediapipe_model",
            mp_model_ok,
            str(mp_path) if mp_model_ok else f"missing: {mp_path}",
            "avfm models download --only mediapipe",
        ),
        Capability(
            "picamera2",
            _module_available("picamera2"),
            f"installed ({_version('picamera2')})"
            if _module_available("picamera2")
            else "not installed",
            "On Raspberry Pi OS: sudo apt install -y python3-picamera2",
        ),
        Capability(
            "adafruit_servokit",
            _module_available("adafruit_servokit"),
            f"installed ({_version('adafruit-circuitpython-servokit')})"
            if _module_available("adafruit_servokit")
            else "not installed",
            "On Raspberry Pi: pip install -e '.[rpi]'",
        ),
    ]
    if config is not None:
        capabilities.append(
            Capability(
                "actuator_config",
                True,
                f"requested={config.actuator.backend}; on_error={config.actuator.on_error}",
            )
        )
        capabilities.append(
            Capability(
                "detector_config",
                True,
                f"mode={config.detector.mode}; backend={config.detector.backend}; "
                f"tracking={config.detector.tracking_backend}; fatigue={config.detector.fatigue_backend}",
            )
        )
        if config.actuator.backend in {"pca9685", "auto"} and probe_actuator:
            try:
                from avfm.actuation.factory import create_actuator

                selection = create_actuator(
                    config.actuator,
                    config.gimbal,
                    park_angles=(config.tracker.default_pan, config.tracker.default_tilt),
                )
                selection.actuator.close()
                capabilities.append(
                    Capability("actuator_probe", True, f"actual={selection.actual_backend}")
                )
            except Exception as exc:
                capabilities.append(
                    Capability(
                        "actuator_probe",
                        False,
                        f"failed: {exc}",
                        "Check I2C wiring and sudo i2cdetect -y 1; use --servo none for passive mode.",
                    )
                )
    if probe_camera_device:
        capabilities.append(probe_camera())
    return capabilities


def doctor_dict(
    config: AppConfig | None = None,
    *,
    probe_camera_device: bool = False,
    probe_actuator: bool = False,
) -> dict:
    capabilities = collect_capabilities(
        config, probe_camera_device=probe_camera_device, probe_actuator=probe_actuator
    )
    return {
        "ok": all(
            capability.available
            for capability in capabilities
            if capability.name in {"python", "avfm", "numpy", "opencv"}
        ),
        "capabilities": [capability.to_dict() for capability in capabilities],
    }
