"""OpenCV overlay renderer (no GUI calls; safe in headless tests)."""

from __future__ import annotations

import cv2
import numpy as np

from avfm.metrics.ear import LEFT_EYE, RIGHT_EYE
from avfm.types import FatigueState, PipelineResult

_GREEN = (64, 220, 64)
_RED = (40, 40, 230)
_AMBER = (0, 180, 255)
_WHITE = (245, 245, 245)
_GREY = (160, 160, 160)


def _state_color(state: FatigueState) -> tuple[int, int, int]:
    if state == FatigueState.DROWSY:
        return _RED
    if state == FatigueState.DISTRACTED:
        return _AMBER
    if state in {FatigueState.NO_FACE, FatigueState.UNAVAILABLE}:
        return _GREY
    return _GREEN


class OverlayRenderer:
    """Compact default HUD for normal desktop and passive use.

    The demo-only large typography and ``--overlay-scale`` switch were removed
    in v0.1.2. Information fixes (real camera FPS, ``EAR --`` for invalid
    samples, immediate eye-closure and drowsiness cause) are retained.
    """

    def __init__(self) -> None:
        self._last_frame_ts: float | None = None
        self._fps_ema: float | None = None

    def _update_fps(self, result: PipelineResult) -> None:
        frame = result.frame
        if frame is None:
            return
        if self._last_frame_ts is not None and frame.timestamp > self._last_frame_ts:
            instant = 1.0 / (frame.timestamp - self._last_frame_ts)
            self._fps_ema = (
                instant if self._fps_ema is None else 0.8 * self._fps_ema + 0.2 * instant
            )
        self._last_frame_ts = frame.timestamp

    def draw(
        self, frame: np.ndarray, result: PipelineResult, *, mode: str = "active"
    ) -> np.ndarray:
        image = frame.copy()
        height, width = image.shape[:2]
        scale = max(0.4, min(1.0, width / 960.0))
        self._update_fps(result)

        # Tracking box and centre reticle.
        bbox = result.observation.bbox if result.observation is not None else None
        if bbox is not None:
            x, y, w, h = (int(value) for value in bbox.to_pixels((width, height)))
            cv2.rectangle(image, (x, y), (x + w, y + h), _GREEN, 2)
        cx, cy = width // 2, height // 2
        cv2.line(image, (cx - 18, cy), (cx + 18, cy), _AMBER, 1)
        cv2.line(image, (cx, cy - 18), (cx, cy + 18), _AMBER, 1)

        # Eye landmarks, if the fatigue detector supplied them.
        fatigue_obs = result.fatigue_observation
        if fatigue_obs is not None and fatigue_obs.detection.landmarks is not None:
            landmarks = fatigue_obs.detection.landmarks
            for index in LEFT_EYE + RIGHT_EYE:
                if index < len(landmarks):
                    lm = landmarks[index]
                    cv2.circle(
                        image,
                        (int(lm.x * width), int(lm.y * height)),
                        max(1, int(2 * scale)),
                        _WHITE,
                        -1,
                    )

        # Compact top status bar.
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (width, int(62 * scale)), (22, 22, 22), -1)
        cv2.addWeighted(overlay, 0.82, image, 0.18, 0, image)

        fatigue = result.fatigue
        if fatigue is not None:
            state = fatigue.state.value
            color = _state_color(fatigue.state)
            ear_text = f"{fatigue.ear:.2f}" if fatigue.ear > 0.0 or fatigue.eyes_closed else "--"
            perclos = f"{fatigue.perclos:.2f}" + ("" if fatigue.perclos_ready else " WARMUP")
            metric_text = f"EAR {ear_text}   PERCLOS {perclos}"
        else:
            state = "FATIGUE OFF"
            color = _GREY
            metric_text = "EAR --   PERCLOS --"

        cv2.putText(
            image,
            state,
            (12, int(26 * scale)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65 * scale,
            color,
            max(1, int(2 * scale)),
        )
        cv2.putText(
            image,
            metric_text,
            (12, int(50 * scale)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46 * scale,
            _WHITE,
            1,
        )

        # Right side: immediate eye closure, drowsiness cause, or tracker state.
        tracker = result.tracker
        if fatigue is not None and fatigue.eyes_closed:
            track_text = "EYES CLOSED"
            track_color = _RED
        elif fatigue is not None and fatigue.state == FatigueState.DROWSY and fatigue.reason:
            track_text = fatigue.reason.upper()
            track_color = _RED
        elif tracker is not None:
            track_text = tracker.state.value.replace("FACE_LOST", "LOST")
            track_color = _WHITE
        else:
            track_text = ""
            track_color = _WHITE

        if track_text:
            (track_w, _), _ = cv2.getTextSize(track_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45 * scale, 1)
            cv2.putText(
                image,
                track_text,
                (width - 12 - track_w, int(26 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45 * scale,
                track_color,
                1,
            )

        if result.loop_ms > 0:
            fps_text = f"CAM {self._fps_ema:.1f} FPS" if self._fps_ema is not None else "CAM -- FPS"
            (fps_w, _), _ = cv2.getTextSize(fps_text, cv2.FONT_HERSHEY_SIMPLEX, 0.42 * scale, 1)
            cv2.putText(
                image,
                fps_text,
                (width - 12 - fps_w, int(50 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42 * scale,
                _AMBER,
                1,
            )

        command = result.command
        if command is not None:
            cv2.putText(
                image,
                f"TARGET PAN {command.pan:.1f}  TILT {command.tilt:.1f}  [{mode.upper()}]",
                (12, int(74 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42 * scale,
                _GREEN if command.applied else _AMBER,
                1,
            )
        return image
