from __future__ import annotations

from pathlib import Path

import numpy as np

from avfm.app.recorder import SessionRecorder, VideoRecorder
from avfm.config import AppConfig
from avfm.types import RunReport


def test_video_recorder(tmp_path: Path) -> None:
    path = tmp_path / "video.mp4"
    recorder = VideoRecorder(path, 10.0, (64, 48))
    try:
        for _ in range(3):
            recorder.write_video(np.zeros((48, 64, 3), dtype=np.uint8))
    finally:
        recorder.close()
    assert path.exists()
    assert path.stat().st_size > 0


def test_session_recorder_video(tmp_path: Path, config: AppConfig) -> None:
    recorder = SessionRecorder(
        tmp_path / "session",
        config=config,
        source="test",
        detector="fake",
        actuator="none",
        frame_size=(64, 48),
        record_video=True,
    )
    recorder.write_video(np.zeros((48, 64, 3), dtype=np.uint8))
    report = RunReport(frames=1)
    recorder.finalize(report)
    recorder.close()
    assert (tmp_path / "session" / "annotated.mp4").exists()
    assert (tmp_path / "session" / "run.json").exists()
