"""Pipeline orchestration: perception → tracking/fatigue → actuation."""

from __future__ import annotations

import dataclasses
import logging
import statistics
import time
from typing import Any

from avfm.actuation.factory import ActuatorSelection
from avfm.clock import Clock
from avfm.config import AppConfig
from avfm.control.tracker import FaceTracker
from avfm.detection.factory import DetectorSet
from avfm.events import EventBus
from avfm.fatigue.calibration import EarCalibration
from avfm.fatigue.monitor import FatigueMonitor
from avfm.metrics import CameraModel, compute_face_metrics
from avfm.perception.pipeline import Perception
from avfm.types import (
    BBox,
    Event,
    EventType,
    FaceDetection,
    FaceMetrics,
    FaceObservation,
    Frame,
    GimbalCommand,
    PipelineResult,
    RunReport,
)

logger = logging.getLogger("avfm.pipeline")


class Pipeline:
    def __init__(
        self,
        config: AppConfig,
        detectors: DetectorSet,
        actuator: ActuatorSelection,
        *,
        event_bus: EventBus | None = None,
        recorder: Any | None = None,
        calibration: EarCalibration | None = None,
        dry_run: bool = False,
        clock: Clock | None = None,
    ) -> None:
        self.config = config
        self.detectors = detectors
        self.actuator_selection = actuator
        self.actuator = actuator.actuator
        self.mode = actuator.mode
        self.dry_run = dry_run
        self.clock = clock
        self.event_bus = event_bus or EventBus()
        self.recorder = recorder
        self.perception = Perception(detectors)
        self.tracker = FaceTracker(
            config.tracker,
            config.gimbal,
            can_actuate=self.actuator.can_move,
            event_bus=self.event_bus,
        )
        available = detectors.fatigue is not None and config.fatigue.enabled
        self.fatigue = FatigueMonitor(
            config.fatigue,
            event_bus=self.event_bus,
            calibration=calibration,
            available=available,
        )
        self._camera_models: dict[tuple[int, int], CameraModel] = {}
        self._frame_index = 0
        self._first_ts: float | None = None
        self._last_ts: float | None = None
        self._loop_times: list[float] = []
        self._tracking_detect_times: list[float] = []
        self._fatigue_detect_times: list[float] = []
        self._last_actuator_error: Exception | None = None
        self.report = RunReport(
            mode=self.mode,
            detector_mode=detectors.mode,
            actuator=actuator.actual_backend,
        )

    def _camera_model(self, frame_size: tuple[int, int]) -> CameraModel:
        if frame_size not in self._camera_models:
            self._camera_models[frame_size] = CameraModel.from_fov(
                frame_size[0], frame_size[1], self.config.camera.hfov_deg
            )
        return self._camera_models[frame_size]

    def _record(self, result: PipelineResult) -> None:
        if self.recorder is None:
            return
        try:
            self.recorder.record_observation(result.observation, result.metrics)
            self.recorder.record_command(
                result.command, result.frame.timestamp if result.frame else 0.0
            )
            if result.fatigue is not None:
                self.recorder.record_fatigue(result.fatigue)
            for event in result.events:
                self.recorder.record_event(event)
            if result.frame is not None and not self.dry_run:
                pass  # video frames are written by the runner after overlay
        except Exception as exc:
            logger.warning("recorder disabled after error: %s", exc)
            self.recorder = None

    def _apply_command(self, command: GimbalCommand) -> tuple[GimbalCommand, list[Event]]:
        events: list[Event] = []
        if self.dry_run or not self.actuator.can_move:
            return command, events
        applied = self.actuator.apply(command)
        if applied:
            command = dataclasses.replace(command, applied=True)
        if (
            self.actuator.last_error is not None
            and self.actuator.last_error is not self._last_actuator_error
        ):
            self._last_actuator_error = self.actuator.last_error
            event = self.event_bus.emit(
                EventType.ACTUATOR_ERROR,
                time.monotonic(),
                {"error": str(self.actuator.last_error)},
            )
            events.append(event)
        self.tracker.set_can_actuate(self.actuator.can_move)
        return command, events

    def process_frame(self, frame: Frame) -> PipelineResult:
        started = time.perf_counter()
        if self._first_ts is None:
            self._first_ts = frame.timestamp
        self._last_ts = frame.timestamp

        perception = self.perception.process(frame, self._frame_index)
        self._frame_index += 1
        if perception.tracking_detect_ms:
            self._tracking_detect_times.append(perception.tracking_detect_ms)
        if perception.fatigue_detect_ms:
            self._fatigue_detect_times.append(perception.fatigue_detect_ms)

        metrics: FaceMetrics | None = None
        if perception.fatigue_obs is not None:
            metrics = compute_face_metrics(
                perception.fatigue_obs,
                self._camera_model(perception.fatigue_obs.frame_size),
                max_reproj_error_px=self.config.fatigue.max_reproj_error_px,
            )

        tracker_result = self.tracker.update(perception.tracking_obs, frame.timestamp)
        fatigue_snapshot = self.fatigue.update(
            metrics,
            frame.timestamp,
            detection_ran=perception.fatigue_ran,
        )
        command, actuator_events = self._apply_command(tracker_result.command)
        events = list(tracker_result.events) + list(fatigue_snapshot.events) + actuator_events

        loop_ms = (time.perf_counter() - started) * 1000.0
        self._loop_times.append(loop_ms)
        self.report.frames += 1
        self._update_report(events)

        observation = perception.tracking_obs or perception.fatigue_obs
        result = PipelineResult(
            frame=frame,
            observation=observation,
            metrics=metrics,
            tracker=tracker_result,
            fatigue=fatigue_snapshot,
            command=command,
            events=tuple(events),
            loop_ms=loop_ms,
            fatigue_observation=perception.fatigue_obs,
        )
        self._record(result)
        return result

    def process_replay(
        self,
        bbox: BBox,
        metrics: FaceMetrics | None,
        timestamp: float,
        frame_size: tuple[int, int],
    ) -> PipelineResult:
        detection = FaceDetection(bbox=bbox, landmarks=None, score=1.0, detector="replay")
        observation = FaceObservation(
            detection=detection, frame_size=frame_size, timestamp=timestamp
        )
        tracker_result = self.tracker.update(observation, timestamp)
        fatigue_snapshot = self.fatigue.update(metrics, timestamp, detection_ran=True)
        command, actuator_events = self._apply_command(tracker_result.command)
        events = list(tracker_result.events) + list(fatigue_snapshot.events) + actuator_events
        self._update_report(events)
        return PipelineResult(
            frame=None,
            observation=observation,
            metrics=metrics,
            tracker=tracker_result,
            fatigue=fatigue_snapshot,
            command=command,
            events=tuple(events),
            loop_ms=0.0,
            fatigue_observation=None,
        )

    def _update_report(self, events: list[Event]) -> None:
        for event in events:
            if event.type == EventType.FACE_LOST:
                self.report.face_lost_count += 1
            elif event.type == EventType.DROWSY_STARTED:
                self.report.drowsy_count += 1
            elif event.type == EventType.DISTRACTED_STARTED:
                self.report.distracted_count += 1
            elif event.type == EventType.ACTUATOR_ERROR:
                self.report.errors += 1

    def finalize_report(self) -> RunReport:
        report = self.report
        if self._first_ts is not None and self._last_ts is not None:
            report.started_at = self._first_ts
            report.ended_at = self._last_ts
        duration = report.ended_at - report.started_at
        if duration <= 0:
            report.loop_fps = 0.0
            report.tracking_hz = 0.0
            report.fatigue_hz = 0.0
        else:
            report.loop_fps = report.frames / duration
            report.tracking_hz = self.perception.tracking_calls / duration
            report.fatigue_hz = self.perception.fatigue_calls / duration
        if self._loop_times:
            report.avg_loop_ms = statistics.fmean(self._loop_times)
            ordered = sorted(self._loop_times)
            index = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
            report.p95_loop_ms = ordered[index]
        if self._tracking_detect_times:
            report.avg_tracking_detect_ms = statistics.fmean(self._tracking_detect_times)
        if self._fatigue_detect_times:
            report.avg_fatigue_detect_ms = statistics.fmean(self._fatigue_detect_times)
        report.mode = self.mode
        report.detector_mode = self.detectors.mode
        report.actuator = self.actuator_selection.actual_backend
        report.rounds = report.frames
        return report

    def close(self) -> None:
        timestamp = self._last_ts or 0.0
        try:
            self.event_bus.emit(EventType.SHUTDOWN, timestamp, {})
        except Exception:  # pragma: no cover
            logger.exception("shutdown event failed")
        try:
            self.tracker.park(timestamp)
            self.actuator.close()
        finally:
            self.perception.close()
            if self.recorder is not None:
                try:
                    self.recorder.close()
                except Exception:  # pragma: no cover
                    logger.exception("recorder close failed")
