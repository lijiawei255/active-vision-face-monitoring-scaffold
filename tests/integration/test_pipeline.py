from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from avfm.actuation.factory import create_actuator
from avfm.app.overlay import OverlayRenderer
from avfm.app.pipeline import Pipeline
from avfm.app.recorder import SessionRecorder
from avfm.config import AppConfig
from avfm.detection.factory import DetectorSet
from avfm.detection.fake import FakeDetector
from avfm.types import BBox, FaceDetection, TrackerState
from tests.helpers import make_frame, make_metrics


def detection() -> list[FaceDetection]:
    return [FaceDetection(BBox(0.4, 0.3, 0.2, 0.2), None, 1.0, "fake")]


def make_pipeline(
    config: AppConfig,
    *,
    actuator_backend: str = "none",
    recorder=None,
    detections: list[list[FaceDetection]] | None = None,
) -> Pipeline:
    script = detections if detections is not None else [detection() for _ in range(50)]
    detectors = DetectorSet(
        tracking=FakeDetector(script),
        fatigue=FakeDetector(script),
        mode="split",
        tracking_interval_frames=1,
        fatigue_interval_frames=1,
    )
    actuator_config = dataclasses.replace(
        config.actuator,
        backend=actuator_backend,
        assume_camera_moves=actuator_backend == "mock",
    )
    actuator = create_actuator(
        actuator_config,
        config.gimbal,
        park_angles=(config.tracker.default_pan, config.tracker.default_tilt),
    )
    return Pipeline(config, detectors, actuator, recorder=recorder)


def test_passive_pipeline_computes_commands_without_moving(config: AppConfig) -> None:
    pipeline = make_pipeline(config, actuator_backend="none")
    result = pipeline.process_frame(make_frame(timestamp=0.0))
    assert result.tracker is not None
    assert result.tracker.state == TrackerState.TRACKING
    assert result.command is not None
    assert result.command.applied is False
    assert result.observation is not None
    report = pipeline.finalize_report()
    assert report.frames == 1
    assert report.mode == "passive"
    pipeline.close()


def test_active_pipeline_applies_commands(config: AppConfig) -> None:
    pipeline = make_pipeline(config, actuator_backend="mock")
    pipeline.process_frame(make_frame(timestamp=0.0))
    result = pipeline.process_frame(make_frame(timestamp=0.1))
    assert result.command is not None
    assert result.command.applied is True
    pipeline.close()


def test_passive_face_lost_does_not_search(config: AppConfig) -> None:
    pipeline = make_pipeline(
        config,
        actuator_backend="none",
        detections=[detection(), []] + [[] for _ in range(20)],
    )
    pipeline.process_frame(make_frame(timestamp=0.0))
    result = pipeline.process_frame(make_frame(timestamp=0.5))
    assert result.tracker is not None
    assert result.tracker.state == TrackerState.FACE_LOST
    pipeline.close()


def test_session_recorder(tmp_path: Path, config: AppConfig) -> None:
    recorder = SessionRecorder(
        tmp_path / "run",
        config=config,
        source="test",
        detector="fake",
        actuator="none",
        frame_size=(640, 480),
    )
    pipeline = make_pipeline(config, recorder=recorder)
    pipeline.process_frame(make_frame(timestamp=0.0))
    report = pipeline.finalize_report()
    recorder.finalize(report)
    pipeline.close()
    assert (tmp_path / "run" / "run.json").exists()
    lines = (tmp_path / "run" / "session.jsonl").read_text(encoding="utf-8").splitlines()
    assert any(json.loads(line)["type"] == "observation" for line in lines)
    data = json.loads((tmp_path / "run" / "run.json").read_text(encoding="utf-8"))
    assert data["report"]["frames"] == 1


def test_replay_processing(config: AppConfig) -> None:
    pipeline = make_pipeline(config, actuator_backend="mock")
    metrics = make_metrics(timestamp=0.0)
    result = pipeline.process_replay(BBox(0.4, 0.3, 0.2, 0.2), metrics, 0.0, (640, 480))
    assert result.tracker is not None
    assert result.command is not None
    pipeline.close()


def test_overlay_renders(config: AppConfig) -> None:
    pipeline = make_pipeline(config)
    result = pipeline.process_frame(make_frame(timestamp=0.0))
    rendered = OverlayRenderer().draw(result.frame.image, result, mode=pipeline.mode)
    assert rendered.shape == result.frame.image.shape
    assert rendered.dtype == result.frame.image.dtype
    pipeline.close()
