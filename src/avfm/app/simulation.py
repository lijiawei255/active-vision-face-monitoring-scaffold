"""Software-in-the-loop simulation: virtual gimbal, face trajectory, PID."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from avfm.config import AppConfig
from avfm.control.tracker import FaceTracker
from avfm.events import EventBus, ListEventSink
from avfm.types import (
    BBox,
    EventType,
    FaceDetection,
    FaceObservation,
    TrackerState,
)


@dataclass
class GimbalPlant:
    pan: float = 90.0
    tilt: float = 80.0
    tau_s: float = 0.12
    max_rate_deg_s: float = 120.0

    def step(self, target_pan: float, target_tilt: float, dt: float) -> None:
        if dt <= 0:
            return
        alpha = 1.0 - math.exp(-dt / max(self.tau_s, 1e-6))
        max_delta = self.max_rate_deg_s * dt
        delta_pan = max(-max_delta, min(max_delta, (target_pan - self.pan) * alpha))
        delta_tilt = max(-max_delta, min(max_delta, (target_tilt - self.tilt) * alpha))
        self.pan += delta_pan
        self.tilt += delta_tilt


@dataclass
class Scenario:
    name: str
    az_step: float = 20.0
    el_step: float = 0.0
    step_time: float = 2.0
    az_amp: float = 20.0
    el_amp: float = 0.0
    period: float = 8.0
    lost_start: float | None = None
    lost_duration: float = 5.0
    noise_deg: float = 0.0

    def face_angles(self, t: float) -> tuple[float, float] | None:
        if (
            self.lost_start is not None
            and self.lost_start <= t < self.lost_start + self.lost_duration
        ):
            return None
        if self.name == "step":
            return (
                self.az_step if t >= self.step_time else 0.0,
                self.el_step if t >= self.step_time else 0.0,
            )
        if self.name == "sine":
            phase = 2.0 * math.pi * t / max(self.period, 1e-6)
            return (self.az_amp * math.sin(phase), self.el_amp * math.sin(phase))
        if self.name == "lost":
            return (0.0, 0.0)
        if self.name == "noisy":
            return (self.az_amp * math.sin(2 * math.pi * t / max(self.period, 1e-6)), self.el_amp)
        return (0.0, 0.0)


@dataclass
class SimulationReport:
    scenario: str
    duration_s: float
    fps: float
    frames: int = 0
    settled: bool = False
    settle_time_s: float | None = None
    overshoot: float = 0.0
    rmse: float = 0.0
    max_error: float = 0.0
    final_error: float = 0.0
    face_lost_events: int = 0
    search_started: bool = False
    reacquire_time_s: float | None = None
    min_pan: float = 0.0
    max_pan: float = 0.0
    min_tilt: float = 0.0
    max_tilt: float = 0.0
    events: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "duration_s": self.duration_s,
            "fps": self.fps,
            "frames": self.frames,
            "settled": self.settled,
            "settle_time_s": self.settle_time_s,
            "overshoot": self.overshoot,
            "rmse": self.rmse,
            "max_error": self.max_error,
            "final_error": self.final_error,
            "face_lost_events": self.face_lost_events,
            "search_started": self.search_started,
            "reacquire_time_s": self.reacquire_time_s,
            "min_pan": self.min_pan,
            "max_pan": self.max_pan,
            "min_tilt": self.min_tilt,
            "max_tilt": self.max_tilt,
            "events": self.events,
        }


def _project(
    face_az: float,
    face_el: float,
    plant: GimbalPlant,
    config: AppConfig,
    *,
    frame_size: tuple[int, int] = (640, 480),
    bbox_size: float = 0.18,
) -> FaceDetection | None:
    pan_pointing = plant.pan - config.tracker.default_pan
    tilt_pointing = plant.tilt - config.tracker.default_tilt
    rel_az = math.radians(face_az - pan_pointing)
    rel_el = math.radians(face_el - tilt_pointing)
    hfov = math.radians(config.camera.hfov_deg)
    vfov = math.radians(config.camera.hfov_deg * frame_size[1] / frame_size[0])
    ex = math.tan(rel_az) / math.tan(hfov / 2.0)
    ey = math.tan(rel_el) / math.tan(vfov / 2.0)
    if abs(ex) > 1.0 or abs(ey) > 1.0:
        return None
    cx = 0.5 + ex / 2.0
    cy = 0.5 + ey / 2.0
    bbox = BBox(cx - bbox_size / 2, cy - bbox_size / 2, bbox_size, bbox_size).clamp()
    return FaceDetection(bbox=bbox, landmarks=None, score=1.0, detector="sim")


def _signed_ex(face_az: float, plant: GimbalPlant, config: AppConfig) -> float:
    pan_pointing = plant.pan - config.tracker.default_pan
    return math.tan(math.radians(face_az - pan_pointing)) / math.tan(
        math.radians(config.camera.hfov_deg) / 2.0
    )


def _normalised_error(
    face_az: float,
    face_el: float,
    plant: GimbalPlant,
    config: AppConfig,
    frame_size: tuple[int, int] = (640, 480),
) -> float:
    pan_pointing = plant.pan - config.tracker.default_pan
    tilt_pointing = plant.tilt - config.tracker.default_tilt
    ex = math.tan(math.radians(face_az - pan_pointing)) / math.tan(
        math.radians(config.camera.hfov_deg) / 2.0
    )
    vfov = config.camera.hfov_deg * frame_size[1] / frame_size[0]
    ey = math.tan(math.radians(face_el - tilt_pointing)) / math.tan(math.radians(vfov) / 2.0)
    return math.hypot(ex, ey)


def run_simulation(
    scenario: Scenario,
    config: AppConfig,
    *,
    duration: float = 15.0,
    fps: float = 15.0,
    seed: int = 0,
) -> SimulationReport:
    rng = random.Random(seed)
    plant = GimbalPlant(config.tracker.default_pan, config.tracker.default_tilt)
    sink = ListEventSink()
    bus = EventBus([sink])
    tracker = FaceTracker(config.tracker, config.gimbal, can_actuate=True, event_bus=bus)
    report = SimulationReport(scenario=scenario.name, duration_s=duration, fps=fps)
    errors: list[float] = []
    signed_errors: list[float] = []
    settle_candidate: float | None = None
    settle_time: float | None = None
    first_search: float | None = None
    reacquire: float | None = None
    lost_seen = False
    steps = int(duration * fps)
    dt = 1.0 / fps

    for index in range(steps):
        t = index * dt
        angles = scenario.face_angles(t)
        detection = None
        error = 0.0
        signed_ex = 0.0
        if angles is not None:
            az, el = angles
            if scenario.noise_deg:
                az += rng.gauss(0.0, scenario.noise_deg)
                el += rng.gauss(0.0, scenario.noise_deg)
            detection = _project(az, el, plant, config)
            error = _normalised_error(az, el, plant, config)
            signed_ex = _signed_ex(az, plant, config)
        else:
            lost_seen = True

        observation = (
            FaceObservation(detection=detection, frame_size=(640, 480), timestamp=t)
            if detection is not None
            else None
        )
        result = tracker.update(observation, t)
        plant.step(result.command.pan, result.command.tilt, dt)

        if detection is not None:
            errors.append(error)
            report.max_error = max(report.max_error, error)
            if scenario.name == "step" and t >= scenario.step_time:
                signed_errors.append(signed_ex)
                if error < 0.05:
                    if settle_candidate is None:
                        settle_candidate = t
                    elif settle_time is None and t - settle_candidate >= 1.0:
                        settle_time = settle_candidate - scenario.step_time
                else:
                    settle_candidate = None
        if result.state == TrackerState.SEARCHING and first_search is None:
            first_search = t
        if (
            result.state == TrackerState.TRACKING
            and lost_seen
            and first_search is not None
            and reacquire is None
        ):
            reacquire = t - first_search
        if (
            result.command.pan <= config.gimbal.pan_min + 1e-6
            or result.command.pan >= config.gimbal.pan_max - 1e-6
        ):
            pass

        report.min_pan = min(report.min_pan or plant.pan, plant.pan)
        report.max_pan = max(report.max_pan, plant.pan)
        report.min_tilt = min(report.min_tilt or plant.tilt, plant.tilt)
        report.max_tilt = max(report.max_tilt, plant.tilt)
        report.frames += 1

    report.events = [event.type.value for event in sink.events]
    report.face_lost_events = sum(1 for event in sink.events if event.type == EventType.FACE_LOST)
    report.search_started = any(event.type == EventType.SEARCH_STARTED for event in sink.events)
    report.reacquire_time_s = reacquire
    report.settled = settle_time is not None
    report.settle_time_s = settle_time
    if errors:
        report.rmse = math.sqrt(sum(value * value for value in errors) / len(errors))
        report.final_error = errors[-1]
        if scenario.name == "step" and signed_errors:
            report.overshoot = max(0.0, -min(signed_errors))
    return report
