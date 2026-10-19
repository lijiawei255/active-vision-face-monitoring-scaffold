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

    def write_video(self, frame: np.ndarray) -> None:
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

    def write_video(self, frame: np.ndarray) -> None:
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

    def __init__(self, path: str | Path, fps: float, size: tuple[int, int]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(str(self.path), fourcc, float(fps), size)
        if not self._writer.isOpened():
            raise RecordingError(f"Could not open video writer: {self.path}")

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

    def write_video(self, frame: np.ndarray) -> None:
        self._writer.write(frame)

    def finalize(self, report: RunReport) -> None:
        return None

    def close(self) -> None:
        self._writer.release()


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
            if frame_size is None:
                raise RecordingError("frame_size is required for video recording")
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
            "config": config.to_dict() if hasattr(config, "to_dict") else config,
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

    def write_video(self, frame: np.ndarray) -> None:
        if self.video is not None:
            self.video.write_video(frame)

    def finalize(self, report: RunReport) -> None:
        self._run_data["ended_at"] = datetime.now(UTC).isoformat()
        self._run_data["report"] = report.to_dict()
        self._write_run()

    def close(self) -> None:
        self.jsonl.close()
        if self.video is not None:
            self.video.close()
