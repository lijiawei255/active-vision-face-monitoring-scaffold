"""Shared value objects, events and run-report types.

Coordinate conventions
----------------------
* ``Frame.image`` is always BGR ``uint8`` with shape ``(H, W, 3)``.
* ``BBox`` is normalised to ``[0, 1]`` with the origin at the top-left.
* Tracker error is ``(cx / w) * 2 - 1`` and ``(cy / h) * 2 - 1``; positive
  values mean "face is to the right / below the frame centre".
* PID output is degrees per second; ``dt`` is seconds; angles are degrees.
* Timestamps are monotonically increasing seconds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np


class TrackerState(StrEnum):
    TRACKING = "TRACKING"
    FACE_LOST = "FACE_LOST"
    SEARCHING = "SEARCHING"
    IDLE = "IDLE"


class FatigueState(StrEnum):
    ALERT = "ALERT"
    DROWSY = "DROWSY"
    DISTRACTED = "DISTRACTED"
    NO_FACE = "NO_FACE"
    UNAVAILABLE = "UNAVAILABLE"


class EventType(StrEnum):
    FACE_ACQUIRED = "FACE_ACQUIRED"
    FACE_LOST = "FACE_LOST"
    SEARCH_STARTED = "SEARCH_STARTED"
    SEARCH_STOPPED = "SEARCH_STOPPED"
    DROWSY_STARTED = "DROWSY_STARTED"
    DROWSY_ENDED = "DROWSY_ENDED"
    DISTRACTED_STARTED = "DISTRACTED_STARTED"
    DISTRACTED_ENDED = "DISTRACTED_ENDED"
    BLINK = "BLINK"
    ACTUATOR_ERROR = "ACTUATOR_ERROR"
    FATIGUE_UNAVAILABLE = "FATIGUE_UNAVAILABLE"
    CONFIG_WARNING = "CONFIG_WARNING"
    SHUTDOWN = "SHUTDOWN"


@dataclass(frozen=True, slots=True)
class BBox:
    """Normalised face box; ``x``/``y`` are the top-left corner."""

    x: float
    y: float
    w: float
    h: float

    def __post_init__(self) -> None:
        if self.w <= 0.0 or self.h <= 0.0:
            raise ValueError(f"BBox width/height must be positive, got {self.w}x{self.h}")

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    @property
    def area(self) -> float:
        return self.w * self.h

    def to_pixels(self, frame_size: tuple[int, int]) -> tuple[float, float, float, float]:
        width, height = frame_size
        return (self.x * width, self.y * height, self.w * width, self.h * height)

    @classmethod
    def from_pixels(
        cls, x: float, y: float, w: float, h: float, frame_size: tuple[int, int]
    ) -> BBox:
        width, height = frame_size
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid frame size {frame_size}")
        x = max(0.0, min(float(width), float(x)))
        y = max(0.0, min(float(height), float(y)))
        w = max(1.0, min(float(width) - x, float(w)))
        h = max(1.0, min(float(height) - y, float(h)))
        return cls(x / width, y / height, w / width, h / height)

    def clamp(self) -> BBox:
        x0 = max(0.0, min(1.0, self.x))
        y0 = max(0.0, min(1.0, self.y))
        x1 = max(0.0, min(1.0, self.x + self.w))
        y1 = max(0.0, min(1.0, self.y + self.h))
        if x1 <= x0 or y1 <= y0:
            return BBox(0.5, 0.5, 1e-6, 1e-6)
        return BBox(x0, y0, x1 - x0, y1 - y0)

    def iou(self, other: BBox) -> float:
        x0 = max(self.x, other.x)
        y0 = max(self.y, other.y)
        x1 = min(self.x + self.w, other.x + other.w)
        y1 = min(self.y + self.h, other.y + other.h)
        if x1 <= x0 or y1 <= y0:
            return 0.0
        inter = (x1 - x0) * (y1 - y0)
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0


@dataclass(frozen=True, slots=True)
class Frame:
    """A captured frame. ``image`` is BGR uint8."""

    image: np.ndarray
    timestamp: float
    index: int = 0
    source: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.image, np.ndarray):
            raise TypeError("Frame.image must be a numpy array")
        if self.image.ndim != 3 or self.image.shape[2] != 3:
            raise ValueError(f"Frame.image must be HxWx3, got {self.image.shape}")

    @property
    def frame_size(self) -> tuple[int, int]:
        return (int(self.image.shape[1]), int(self.image.shape[0]))


@dataclass(frozen=True, slots=True)
class Landmark:
    """Normalised MediaPipe landmark. ``z`` is relative depth."""

    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True, slots=True)
class FaceDetection:
    """Detector output for one face."""

    bbox: BBox
    landmarks: tuple[Landmark, ...] | None = None
    score: float = 0.0
    detector: str = "unknown"


@dataclass(frozen=True, slots=True)
class FaceObservation:
    """Detection tied to a frame and a monotonic timestamp."""

    detection: FaceDetection
    frame_size: tuple[int, int]
    timestamp: float

    @property
    def bbox(self) -> BBox:
        return self.detection.bbox


@dataclass(frozen=True, slots=True)
class FaceMetrics:
    """Per-face geometry/fatigue features computed once per observation."""

    ear: float = 0.0
    left_ear: float = 0.0
    right_ear: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    valid_landmarks: bool = False
    valid_pose: bool = False
    reproj_error: float = float("inf")
    timestamp: float = 0.0

    @property
    def pose_ok(self) -> bool:
        return self.valid_pose


@dataclass(frozen=True, slots=True)
class GimbalCommand:
    """Desired pan/tilt angles and rates. ``applied`` is set by the actuator."""

    pan: float
    tilt: float
    pan_rate: float = 0.0
    tilt_rate: float = 0.0
    applied: bool = False
    reason: str = "track"


@dataclass(frozen=True, slots=True)
class Event:
    type: EventType
    timestamp: float
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type.value, "t": self.timestamp, "payload": self.payload}


@dataclass(frozen=True, slots=True)
class TrackerResult:
    state: TrackerState
    command: GimbalCommand
    bbox: BBox | None
    events: tuple[Event, ...] = ()


@dataclass(frozen=True, slots=True)
class FatigueSnapshot:
    state: FatigueState
    timestamp: float = 0.0
    ear: float = 0.0
    perclos: float = 0.0
    perclos_ready: bool = False
    coverage: float = 0.0
    eyes_closed: bool = False
    looking_away: bool = False
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    blink_rate: float = 0.0
    reason: str = ""
    events: tuple[Event, ...] = ()


@dataclass(frozen=True, slots=True)
class PerceptionResult:
    """Result of one perception tick.

    ``tracking_ran``/``fatigue_ran`` tell the caller whether a detector was
    actually invoked on this frame (as opposed to a skipped frame).
    """

    tracking_obs: FaceObservation | None = None
    fatigue_obs: FaceObservation | None = None
    tracking_ran: bool = False
    fatigue_ran: bool = False
    tracking_detect_ms: float = 0.0
    fatigue_detect_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class PipelineResult:
    frame: Frame | None
    observation: FaceObservation | None
    metrics: FaceMetrics | None
    tracker: TrackerResult | None
    fatigue: FatigueSnapshot | None
    command: GimbalCommand | None
    events: tuple[Event, ...] = ()
    loop_ms: float = 0.0
    fatigue_observation: FaceObservation | None = None


@dataclass
class RunReport:
    """Serialisable run summary, including performance counters."""

    started_at: float = 0.0
    ended_at: float = 0.0
    frames: int = 0
    dropped_frames: int = 0
    loop_fps: float = 0.0
    tracking_hz: float = 0.0
    fatigue_hz: float = 0.0
    avg_loop_ms: float = 0.0
    p95_loop_ms: float = 0.0
    avg_tracking_detect_ms: float = 0.0
    avg_fatigue_detect_ms: float = 0.0
    face_lost_count: int = 0
    drowsy_count: int = 0
    distracted_count: int = 0
    errors: int = 0
    mode: str = "unknown"
    detector_mode: str = "unknown"
    actuator: str = "unknown"
    rounds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "frames": self.frames,
            "dropped_frames": self.dropped_frames,
            "loop_fps": self.loop_fps,
            "tracking_hz": self.tracking_hz,
            "fatigue_hz": self.fatigue_hz,
            "avg_loop_ms": self.avg_loop_ms,
            "p95_loop_ms": self.p95_loop_ms,
            "avg_tracking_detect_ms": self.avg_tracking_detect_ms,
            "avg_fatigue_detect_ms": self.avg_fatigue_detect_ms,
            "face_lost_count": self.face_lost_count,
            "drowsy_count": self.drowsy_count,
            "distracted_count": self.distracted_count,
            "errors": self.errors,
            "mode": self.mode,
            "detector_mode": self.detector_mode,
            "actuator": self.actuator,
            "rounds": self.rounds,
        }
