from __future__ import annotations

import numpy as np
import pytest

from avfm.capture.opencv import OpenCVFrameSource


@pytest.mark.webcam
def test_webcam_reads_one_frame() -> None:
    source = OpenCVFrameSource(
        "webcam",
        0,
        width=640,
        height=480,
        fps=15,
        flip="none",
    )
    source.open()
    try:
        frame = source.read()
        if frame is None:
            pytest.skip("Webcam did not return a frame")
        assert isinstance(frame.image, np.ndarray)
        assert frame.image.ndim == 3
        assert frame.image.shape[2] == 3
    finally:
        source.close()
