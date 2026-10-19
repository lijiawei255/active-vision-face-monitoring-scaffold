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
_BG = (18, 18, 18)

_FONT = cv2.FONT_HERSHEY_DUPLEX


def _state_color(state: FatigueState) -> tuple[int, int, int]:
    if state in {FatigueState.DROWSY}:
        return _RED
    if state in {FatigueState.DISTRACTED}:
        return _AMBER
    if state in {FatigueState.NO_FACE, FatigueState.UNAVAILABLE}:
        return _GREY
    return _GREEN


class OverlayRenderer:
    """Draw a large, high-contrast HUD suitable for phone viewing.

    ``scale`` multiplies the font/line sizes. ``None`` uses a resolution-aware
    default; a demo or mobile recording can pass e.g. ``scale=1.5``.
    """

    def __init__(self, *, scale: float | None = None) -> None:
        self.scale = scale
        self._font = _FONT
        self._last_frame_ts: float | None = None
        self._fps_ema: float | None = None

    def _update_fps(self, result: PipelineResult) -> None:
        frame = result.frame
        if frame is None:
            return
        if self._last_frame_ts is not None and frame.timestamp > self._last_frame_ts:
            dt = frame.timestamp - self._last_frame_ts
            instant = 1.0 / dt
            self._fps_ema = (
                instant if self._fps_ema is None else 0.8 * self._fps_ema + 0.2 * instant
            )
        self._last_frame_ts = frame.timestamp

    @staticmethod
    def _scale_for(width: int, requested: float | None) -> float:
        if requested is not None:
            return max(0.5, min(2.5, float(requested)))
        return max(0.7, min(1.2, width / 900.0))

    def _text(
        self,
        image: np.ndarray,
        text: str,
        origin: tuple[int, int],
        size: float,
        color: tuple[int, int, int],
        thickness: int,
    ) -> None:
        # Black outline first; colour fill on top. This survives compression
        # and remains readable on a phone screen.
        cv2.putText(
            image,
            text,
            origin,
            self._font,
            size,
            (0, 0, 0),
            thickness + 2,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            text,
            origin,
            self._font,
            size,
            color,
            thickness,
            cv2.LINE_AA,
        )

    def draw(
        self, frame: np.ndarray, result: PipelineResult, *, mode: str = "active"
    ) -> np.ndarray:
        image = frame.copy()
        height, width = image.shape[:2]
        s = self._scale_for(width, self.scale)
        thickness = max(1, int(round(2.0 * s)))
        self._update_fps(result)

        # --- top panel -----------------------------------------------------
        panel_h = min(height // 3, int(78 * s))
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (width, panel_h), _BG, -1)
        cv2.addWeighted(overlay, 0.82, image, 0.18, 0, image)

        fatigue = result.fatigue
        state = FatigueState.UNAVAILABLE if fatigue is None else fatigue.state
        color = _state_color(state)
        state_text = "FATIGUE OFF" if fatigue is None else state.value
        self._text(
            image,
            state_text,
            (int(14 * s), int(46 * s)),
            1.25 * s,
            color,
            thickness + 1,
        )
        if fatigue is not None:
            ear_text = f"{fatigue.ear:.2f}" if fatigue.ear > 0.0 or fatigue.eyes_closed else "--"
            perclos = f"{fatigue.perclos:.2f}" + ("" if fatigue.perclos_ready else " WARMUP")
            metric_text = f"EAR {ear_text}   PERCLOS {perclos}"
        else:
            metric_text = "EAR --   PERCLOS --"
        self._text(
            image,
            metric_text,
            (int(16 * s), int(72 * s)),
            0.68 * s,
            _WHITE,
            max(1, thickness - 1),
        )

        # Right side: immediate eye-closure badge, or the drowsiness cause,
        # or the tracker state.
        tracker = result.tracker
        eyes_closed = bool(fatigue is not None and fatigue.eyes_closed)
        if eyes_closed:
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
            (track_w, _), _ = cv2.getTextSize(
                track_text, self._font, 0.6 * s, max(1, thickness - 1)
            )
            self._text(
                image,
                track_text,
                (width - int(14 * s) - track_w, int(46 * s)),
                0.6 * s,
                track_color,
                max(1, thickness - 1),
            )
        cv2.rectangle(
            image,
            (0, panel_h - max(2, int(4 * s))),
            (width, panel_h),
            color,
            -1,
        )

        # --- tracking box and reticle -------------------------------------
        bbox = result.observation.bbox if result.observation is not None else None
        if bbox is not None:
            x, y, w, h = (int(value) for value in bbox.to_pixels((width, height)))
            cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness + 1)
        cx, cy = width // 2, height // 2
        arm = max(12, int(22 * s))
        cv2.line(image, (cx - arm, cy), (cx + arm, cy), _AMBER, thickness)
        cv2.line(image, (cx, cy - arm), (cx, cy + arm), _AMBER, thickness)

        # Eye landmarks, if the fatigue detector supplied them.
        fatigue_obs = result.fatigue_observation
        if fatigue_obs is not None and fatigue_obs.detection.landmarks is not None:
            landmarks = fatigue_obs.detection.landmarks
            radius = max(2, int(3 * s))
            for index in LEFT_EYE + RIGHT_EYE:
                if index < len(landmarks):
                    lm = landmarks[index]
                    cv2.circle(
                        image,
                        (int(lm.x * width), int(lm.y * height)),
                        radius,
                        _WHITE,
                        -1,
                    )

        # --- bottom panel: two lines so the command and FPS never collide.
        bottom_h = min(height // 4, int(54 * s))
        overlay = image.copy()
        cv2.rectangle(overlay, (0, height - bottom_h), (width, height), _BG, -1)
        cv2.addWeighted(overlay, 0.78, image, 0.22, 0, image)
        command = result.command
        if command is not None:
            self._text(
                image,
                f"TARGET PAN {command.pan:.1f}   TILT {command.tilt:.1f}",
                (int(14 * s), height - int(31 * s)),
                0.62 * s,
                _GREEN if command.applied else _AMBER,
                max(1, thickness - 1),
            )
        self._text(
            image,
            mode.upper(),
            (int(14 * s), height - int(9 * s)),
            0.55 * s,
            _GREY,
            max(1, thickness - 1),
        )
        if result.loop_ms > 0:
            fps_text = f"CAM {self._fps_ema:.1f} FPS" if self._fps_ema is not None else "CAM -- FPS"
            (fps_w, _), _ = cv2.getTextSize(fps_text, self._font, 0.6 * s, max(1, thickness - 1))
            self._text(
                image,
                fps_text,
                (width - int(14 * s) - fps_w, height - int(31 * s)),
                0.6 * s,
                _AMBER,
                max(1, thickness - 1),
            )

        # A full-frame red border is visible even on a small phone screen.
        if fatigue is not None and fatigue.state == FatigueState.DROWSY:
            cv2.rectangle(
                image,
                (0, 0),
                (width - 1, height - 1),
                _RED,
                max(4, int(7 * s)),
            )
        return image
