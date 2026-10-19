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


class OverlayRenderer:
    def draw(
        self, frame: np.ndarray, result: PipelineResult, *, mode: str = "active"
    ) -> np.ndarray:
        image = frame.copy()
        height, width = image.shape[:2]
        scale = max(0.4, min(1.0, width / 960.0))

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

        # Top status bar.
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (width, int(62 * scale)), (22, 22, 22), -1)
        cv2.addWeighted(overlay, 0.82, image, 0.18, 0, image)

        fatigue = result.fatigue
        if fatigue is not None:
            state = fatigue.state.value
            color = (
                _RED if fatigue.state in {FatigueState.DROWSY, FatigueState.DISTRACTED} else _GREEN
            )
            if fatigue.state == FatigueState.NO_FACE:
                color = _GREY
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
                f"EAR {fatigue.ear:.2f}  PERCLOS {fatigue.perclos:.2f}"
                + ("" if fatigue.perclos_ready else " (warmup)"),
                (12, int(50 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48 * scale,
                _WHITE,
                1,
            )
        else:
            cv2.putText(
                image,
                "FATIGUE DISABLED",
                (12, int(30 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55 * scale,
                _GREY,
                1,
            )

        command = result.command
        if command is not None:
            cv2.putText(
                image,
                f"pan {command.pan:.1f}  tilt {command.tilt:.1f}  [{mode}]",
                (12, int(74 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45 * scale,
                _AMBER if not command.applied else _GREEN,
                1,
            )

        tracker = result.tracker
        if tracker is not None:
            cv2.putText(
                image,
                f"tracker {tracker.state.value}",
                (width - int(210 * scale), int(26 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45 * scale,
                _WHITE,
                1,
            )
        if result.loop_ms > 0:
            cv2.putText(
                image,
                f"{1000.0 / result.loop_ms:.1f} FPS",
                (width - int(130 * scale), int(50 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45 * scale,
                _WHITE,
                1,
            )
        return image
