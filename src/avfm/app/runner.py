"""Main capture/process/display loop."""

from __future__ import annotations

import contextlib
import logging

import cv2

from avfm.app.overlay import OverlayRenderer
from avfm.app.pipeline import Pipeline
from avfm.capture.base import FrameSource
from avfm.clock import Clock, MonotonicClock
from avfm.errors import CameraError, RecordingError
from avfm.types import RunReport

logger = logging.getLogger("avfm.runner")


class Runner:
    def __init__(
        self, *, clock: Clock | None = None, overlay: OverlayRenderer | None = None
    ) -> None:
        self.clock = clock or MonotonicClock()
        self.overlay = overlay or OverlayRenderer()

    def run(
        self,
        source: FrameSource,
        pipeline: Pipeline,
        *,
        duration: float | None = None,
        max_frames: int | None = None,
        target_fps: float | None = None,
        show: bool = False,
        realtime: bool = True,
        record_video: bool = False,
    ) -> RunReport:
        recorder = pipeline.recorder
        video_enabled = bool(
            record_video and recorder is not None and getattr(recorder, "video_enabled", False)
        )
        first_ts: float | None = None
        read_failures = 0
        max_read_failures = 20
        stop = False

        try:
            source.open()
            while not stop:
                frame = source.read()
                if frame is None:
                    # Image and video sources end cleanly; a live camera returning
                    # None is a transient/device failure.
                    if source.description.startswith(("image:", "video:")):
                        break
                    read_failures += 1
                    if read_failures >= max_read_failures:
                        raise CameraError(
                            f"Camera source {source.description} returned no frames "
                            f"{read_failures} times. Check the device and permissions."
                        )
                    self.clock.sleep(0.01)
                    continue
                read_failures = 0
                if first_ts is None:
                    first_ts = frame.timestamp

                # Drop stale frames from a buffered webcam queue.
                if (
                    source.description.startswith("webcam")
                    and self.clock.now() - frame.timestamp > pipeline.config.runtime.max_frame_age_s
                ):
                    pipeline.report.dropped_frames += 1
                    continue

                frame_started = self.clock.now()
                result = pipeline.process_frame(frame)

                annotated = None
                if show or video_enabled:
                    annotated = self.overlay.draw(frame.image, result, mode=pipeline.mode)
                if show and annotated is not None:
                    try:
                        cv2.imshow("avfm", annotated)
                        key = cv2.waitKey(1) & 0xFF
                        if key in (ord("q"), 27):
                            stop = True
                    except cv2.error:
                        logger.warning("OpenCV display unavailable; continuing headless")
                        show = False
                if video_enabled and annotated is not None and recorder is not None:
                    try:
                        recorder.write_video(  # type: ignore[attr-defined]
                            annotated, timestamp=frame.timestamp
                        )
                    except Exception as exc:
                        raise RecordingError(f"Video recording failed: {exc}") from exc

                if pipeline.actuator.stop_requested:
                    stop = True

                if max_frames is not None and pipeline.report.frames >= max_frames:
                    break
                if duration is not None and frame.timestamp - first_ts >= duration:
                    break

                if target_fps and (source.description.startswith("webcam") or realtime):
                    remaining = max(0.0, 1.0 / target_fps - (self.clock.now() - frame_started))
                    if remaining:
                        self.clock.sleep(remaining)
        finally:
            report = pipeline.finalize_report()
            if recorder is not None:
                try:
                    recorder.finalize(report)
                except Exception:  # pragma: no cover - disk errors
                    logger.exception("recorder finalize failed")
            pipeline.close()
            source.close()
            with contextlib.suppress(Exception):
                cv2.destroyAllWindows()
        return report


def run_source(
    source: FrameSource,
    pipeline: Pipeline,
    *,
    duration: float | None = None,
    max_frames: int | None = None,
    target_fps: float | None = None,
    show: bool = False,
    realtime: bool = True,
    record_video: bool = False,
    clock: Clock | None = None,
) -> RunReport:
    return Runner(clock=clock).run(
        source,
        pipeline,
        duration=duration,
        max_frames=max_frames,
        target_fps=target_fps,
        show=show,
        realtime=realtime,
        record_video=record_video,
    )
