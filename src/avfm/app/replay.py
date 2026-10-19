"""Replay JSONL sessions without camera, detector or hardware."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from avfm.actuation.factory import create_actuator
from avfm.app.pipeline import Pipeline
from avfm.config import AppConfig
from avfm.detection.factory import DetectorSet
from avfm.detection.fake import FakeDetector
from avfm.events import EventBus, ListEventSink
from avfm.fatigue.calibration import EarCalibration
from avfm.types import BBox, FaceMetrics


def load_session(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _metrics_from_record(record: dict[str, Any]) -> FaceMetrics | None:
    data = record.get("metrics")
    if not isinstance(data, dict):
        return None
    known = {field.name for field in dataclasses.fields(FaceMetrics)}
    return FaceMetrics(**{key: value for key, value in data.items() if key in known})


def replay_session(
    path: str | Path,
    config: AppConfig,
    *,
    compare: bool = False,
) -> dict[str, Any]:
    records = load_session(path)
    actuator_config = dataclasses.replace(config.actuator, backend="mock", assume_camera_moves=True)
    actuator = create_actuator(
        actuator_config,
        config.gimbal,
        park_angles=(config.tracker.default_pan, config.tracker.default_tilt),
    )
    sink = ListEventSink()
    pipeline = Pipeline(
        config,
        DetectorSet(
            tracking=FakeDetector(),
            fatigue=FakeDetector(),
            mode="single",
            tracking_interval_frames=1,
            fatigue_interval_frames=1,
        ),
        actuator,
        event_bus=EventBus([sink]),
        calibration=_load_calibration(config),
    )
    produced_commands: list[dict[str, Any]] = []
    produced_events: list[str] = []
    for record in records:
        if record.get("type") != "observation":
            continue
        bbox_values = record.get("bbox")
        if not bbox_values:
            continue
        bbox = BBox(*[float(value) for value in bbox_values])
        metrics = _metrics_from_record(record)
        result = pipeline.process_replay(
            bbox,
            metrics,
            float(record.get("t", 0.0)),
            tuple(record.get("frame_size", (640, 480))),
        )
        if result.command is not None:
            produced_commands.append(
                {"t": record.get("t", 0.0), "pan": result.command.pan, "tilt": result.command.tilt}
            )
        produced_events.extend(event.type.value for event in result.events)
    pipeline.close()

    report: dict[str, Any] = {
        "observations": sum(1 for record in records if record.get("type") == "observation"),
        "commands": produced_commands,
        "events": produced_events + [event.type.value for event in sink.events],
    }
    if compare:
        recorded_commands = [record for record in records if record.get("type") == "command"]
        max_pan_diff = 0.0
        max_tilt_diff = 0.0
        for produced, recorded in zip(produced_commands, recorded_commands, strict=False):
            max_pan_diff = max(max_pan_diff, abs(produced["pan"] - float(recorded.get("pan", 0.0))))
            max_tilt_diff = max(
                max_tilt_diff, abs(produced["tilt"] - float(recorded.get("tilt", 0.0)))
            )
        report["compare"] = {
            "recorded_commands": len(recorded_commands),
            "max_pan_diff_deg": max_pan_diff,
            "max_tilt_diff_deg": max_tilt_diff,
        }
    return report


def _load_calibration(config: AppConfig) -> EarCalibration | None:
    path = config.fatigue.ear_calibration_file
    if not path:
        return None
    try:
        return EarCalibration.load(path)
    except Exception:
        return None
