from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from avfm.capture.opencv import OpenCVFrameSource


def test_video_source_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "test.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (64, 48))
    assert writer.isOpened()
    for _ in range(3):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()

    source = OpenCVFrameSource("video", str(path), width=64, height=48, fps=10)
    source.open()
    try:
        frames = []
        while True:
            frame = source.read()
            if frame is None:
                break
            frames.append(frame)
    finally:
        source.close()
    assert len(frames) == 3
    assert frames[0].timestamp == 0.0
    assert frames[1].timestamp > frames[0].timestamp
