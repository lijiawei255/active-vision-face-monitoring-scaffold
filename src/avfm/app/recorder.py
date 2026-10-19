"""JSONL, video and session recorders.

Privacy default: JSONL contains bounding boxes, metrics and events, never raw
pixels. Video recording is explicit and opt-in.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from avfm import __version__
from avfm.errors import RecordingError
from avfm.types import (
    Event,
    FaceMetrics,
    FaceObservation,
    FatigueSnapshot,
    GimbalCommand,
    RunReport,
)

logger = logging.getLogger("avfm.recorder")


def _bbox_list(obs: FaceObservation) -> list[float]:
    bbox = obs.bbox
    return [bbox.x, bbox.y, bbox.w, bbox.h]


class NullRecorder:
    video_enabled = False

    def record_observation(
        self, observation: FaceObservation | None, metrics: FaceMetrics | None
    ) -> None:
        return None

    def record_command(self, command: GimbalCommand | None, timestamp: float) -> None:
        return None

    def record_fatigue(self, fatigue: FatigueSnapshot) -> None:
        return None

    def record_event(self, event: Event) -> None:
        return None

    def write_video(self, frame: np.ndarray, timestamp: float | None = None) -> None:
        return None

    def finalize(self, report: RunReport) -> None:
        return None

    def close(self) -> None:
        return None


class JsonlRecorder:
    video_enabled = False

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._handle = self.path.open("w", encoding="utf-8")
        except OSError as exc:
            raise RecordingError(f"Could not open JSONL recorder: {exc}") from exc

    def _write(self, record: dict[str, Any]) -> None:
        self._handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._handle.flush()

    def record_observation(
        self, observation: FaceObservation | None, metrics: FaceMetrics | None
    ) -> None:
        if observation is None:
            return
        record: dict[str, Any] = {
            "type": "observation",
            "t": observation.timestamp,
            "frame_size": list(observation.frame_size),
            "bbox": _bbox_list(observation),
            "score": observation.detection.score,
            "detector": observation.detection.detector,
        }
        if metrics is not None:
            record["metrics"] = dataclasses.asdict(metrics)
        self._write(record)

    def record_command(self, command: GimbalCommand | None, timestamp: float) -> None:
        if command is None:
            return
        record = {"type": "command", "t": timestamp}
        record.update(dataclasses.asdict(command))
        self._write(record)

    def record_fatigue(self, fatigue: FatigueSnapshot) -> None:
        self._write(
            {
                "type": "fatigue",
                "t": fatigue.timestamp,
                "state": fatigue.state.value,
                "ear": fatigue.ear,
                "perclos": fatigue.perclos,
                "perclos_ready": fatigue.perclos_ready,
                "coverage": fatigue.coverage,
                "eyes_closed": fatigue.eyes_closed,
                "looking_away": fatigue.looking_away,
                "yaw": fatigue.yaw,
                "pitch": fatigue.pitch,
                "roll": fatigue.roll,
                "blink_rate": fatigue.blink_rate,
                "reason": fatigue.reason,
            }
        )

    def record_event(self, event: Event) -> None:
        self._write({"type": "event", **event.to_dict()})

    def write_video(self, frame: np.ndarray, timestamp: float | None = None) -> None:
        return None

    def finalize(self, report: RunReport) -> None:
        return None

    def close(self) -> None:
        try:
            self._handle.close()
        except Exception:  # pragma: no cover
            logger.exception("JSONL recorder close failed")


class VideoRecorder:
    video_enabled = True

    def __init__(self, path: str | Path, fps: float, size: tuple[int, int] | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fps = float(fps)
        if self.fps <= 0:
            raise RecordingError("Video FPS must be positive")
        # ``size`` is accepted for API compatibility only; the writer is opened
        # lazily from the first actual frame so webcam/image/Picamera resolution
        # changes cannot create a silently stretched or cropped video.
        self._writer: cv2.VideoWriter | None = None
        self._size: tuple[int, int] | None = None
        self._frames_written = 0
        self._start_ts: float | None = None

    @property
    def size(self) -> tuple[int, int] | None:
        return self._size

    def _ensure_writer(self, size: tuple[int, int]) -> None:
        if self._writer is not None:
            if size != self._size:
                raise RecordingError(
                    f"Video frame size changed from {self._size} to {size}; "
                    "keep camera resolution constant during a recording"
                )
            return
        if size[0] <= 0 or size[1] <= 0:
            raise RecordingError(f"Invalid video frame size: {size}")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(str(self.path), fourcc, self.fps, size)
        if not self._writer.isOpened():
            self._writer = None
            raise RecordingError(f"Could not open video writer: {self.path}")
        self._size = size

    def _write_once(self, frame: np.ndarray) -> None:
        if self._writer is None:
            raise RecordingError("Video writer is not open")
        self._writer.write(frame)
        self._frames_written += 1

    def record_observation(
        self, observation: FaceObservation | None, metrics: FaceMetrics | None
    ) -> None:
        return None

    def record_command(self, command: GimbalCommand | None, timestamp: float) -> None:
        return None

    def record_fatigue(self, fatigue: FatigueSnapshot) -> None:
        return None

    def record_event(self, event: Event) -> None:
        return None

    def write_video(self, frame: np.ndarray, timestamp: float | None = None) -> None:
        """Write a frame; with timestamps, duplicate/skip to preserve wall time."""
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise RecordingError(f"Expected a BGR HxWx3 frame, got shape {frame.shape}")
        height, width = frame.shape[:2]
        self._ensure_writer((width, height))

        if timestamp is None:
            self._write_once(frame)
            return

        if self._start_ts is None:
            self._start_ts = timestamp
        # The container FPS is nominal; use source timestamps so a slower loop
        # produces a video matching the real recording duration.
        target = max(1, int(round((timestamp - self._start_ts) * self.fps)) + 1)
        while self._frames_written < target:
            self._write_once(frame)

    def finalize(self, report: RunReport) -> None:
        return None

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None


def _config_for_manifest(config: Any) -> Any:
    """Serialize config without local absolute paths in a shareable run manifest."""
    if not hasattr(config, "to_dict"):
        return config
    data = config.to_dict()
    if isinstance(data, dict):
        data.pop("loaded_from", None)
    return data


class SessionRecorder:
    """Write ``run.json`` + ``session.jsonl`` and optionally an annotated video."""

    def __init__(
        self,
        directory: str | Path,
        *,
        config: Any,
        source: str,
        detector: str,
        actuator: str,
        fps: float = 15.0,
        frame_size: tuple[int, int] | None = None,
        record_video: bool = False,
    ) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.jsonl = JsonlRecorder(self.directory / "session.jsonl")
        self.video: VideoRecorder | None = None
        self.video_enabled = False
        if record_video:
            self.video = VideoRecorder(self.directory / "annotated.mp4", fps, frame_size)
            self.video_enabled = True
        self._run_path = self.directory / "run.json"
        self._run_data: dict[str, Any] = {
            "schema_version": 1,
            "avfm_version": __version__,
            "started_at": datetime.now(UTC).isoformat(),
            "platform": platform.platform(),
            "python": sys.version,
            "source": source,
            "detector": detector,
            "actuator": actuator,
            "config": _config_for_manifest(config),
        }
        self._write_run()

    def _write_run(self) -> None:
        self._run_path.write_text(
            json.dumps(self._run_data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def record_observation(
        self, observation: FaceObservation | None, metrics: FaceMetrics | None
    ) -> None:
        self.jsonl.record_observation(observation, metrics)

    def record_command(self, command: GimbalCommand | None, timestamp: float) -> None:
        self.jsonl.record_command(command, timestamp)

    def record_fatigue(self, fatigue: FatigueSnapshot) -> None:
        self.jsonl.record_fatigue(fatigue)

    def record_event(self, event: Event) -> None:
        self.jsonl.record_event(event)

    def write_video(self, frame: np.ndarray, timestamp: float | None = None) -> None:
        if self.video is not None:
            self.video.write_video(frame, timestamp)

    def finalize(self, report: RunReport) -> None:
        self._run_data["ended_at"] = datetime.now(UTC).isoformat()
        self._run_data["report"] = report.to_dict()
        if self.video is not None and self.video.size is not None:
            self._run_data["video"] = {
                "path": "annotated.mp4",
                "width": self.video.size[0],
                "height": self.video.size[1],
            }
        self._write_run()

    def close(self) -> None:
        self.jsonl.close()
        if self.video is not None:
            self.video.close()
