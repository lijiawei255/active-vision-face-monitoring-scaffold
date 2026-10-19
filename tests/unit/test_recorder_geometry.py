from __future__ import annotations

import cv2
import numpy as np
import pytest

from avfm.app.recorder import RecordingError, VideoRecorder


def test_video_recorder_uses_actual_frame_size(tmp_path) -> None:
    path = tmp_path / "actual.mp4"
    recorder = VideoRecorder(path, 10.0, (640, 480))
    try:
        recorder.write_video(np.zeros((24, 32, 3), dtype=np.uint8))
    finally:
        recorder.close()
    cap = cv2.VideoCapture(str(path))
    try:
        assert cap.isOpened()
        assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == 32
        assert int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) == 24
    finally:
        cap.release()


def test_video_recorder_timestamp_preserves_duration(tmp_path) -> None:
    path = tmp_path / "timed.mp4"
    recorder = VideoRecorder(path, 10.0, (64, 48))
    try:
        for t in (0.0, 0.2, 0.4):
            recorder.write_video(np.zeros((48, 64, 3), dtype=np.uint8), timestamp=t)
    finally:
        recorder.close()
    cap = cv2.VideoCapture(str(path))
    try:
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        assert frames >= 4
    finally:
        cap.release()


def test_video_recorder_rejects_resolution_change(tmp_path) -> None:
    recorder = VideoRecorder(tmp_path / "bad.mp4", 10.0)
    try:
        recorder.write_video(np.zeros((48, 64, 3), dtype=np.uint8))
        with pytest.raises(RecordingError):
            recorder.write_video(np.zeros((24, 32, 3), dtype=np.uint8))
    finally:
        recorder.close()
