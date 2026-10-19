"""Camera source factory."""

from __future__ import annotations

from pathlib import Path

from avfm.capture.base import FrameSource
from avfm.capture.opencv import OpenCVFrameSource
from avfm.capture.picamera2 import Picamera2FrameSource
from avfm.clock import Clock
from avfm.config import CameraConfig
from avfm.errors import ConfigError


def create_source(
    config: CameraConfig,
    clock: Clock | None = None,
    *,
    realtime: bool = False,
) -> FrameSource:
    spec = str(config.source).strip()
    if spec == "picamera":
        return Picamera2FrameSource(
            width=config.width,
            height=config.height,
            fps=config.fps,
            flip=config.flip,
            warmup_s=config.warmup_s,
            clock=clock,
        )

    kind, _, target = spec.partition(":")
    if kind == "webcam":
        index = int(target) if target else 0
        return OpenCVFrameSource(
            "webcam",
            index,
            width=config.width,
            height=config.height,
            fps=config.fps,
            flip=config.flip,
            realtime=True,
            clock=clock,
        )
    if kind in {"video", "image"}:
        if not target:
            raise ConfigError(f"camera.source={spec!r} is missing a path")
        if not Path(target).exists():
            raise ConfigError(f"camera.source path does not exist: {target}")
        return OpenCVFrameSource(
            kind,
            target,
            width=config.width,
            height=config.height,
            fps=config.fps,
            flip=config.flip,
            realtime=realtime,
            clock=clock,
        )
    raise ConfigError(
        f"Unsupported camera.source={spec!r}; use picamera, webcam:N, video:path or image:path"
    )
