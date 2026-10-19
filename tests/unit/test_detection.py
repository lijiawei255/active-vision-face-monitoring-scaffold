from __future__ import annotations

from pathlib import Path

import pytest

from avfm.detection.base import select_primary
from avfm.detection.fake import FakeDetector
from avfm.detection.yunet import YuNetDetector
from avfm.errors import ModelNotFoundError
from avfm.types import BBox, FaceDetection, Frame
from tests.helpers import make_frame

REPO_ROOT = Path(__file__).resolve().parents[2]
ASTRONAUT = REPO_ROOT / "tests" / "data" / "astronaut.jpg"
YUNET_MODEL = REPO_ROOT / "models" / "yunet" / "face_detection_yunet_2026may.onnx"
MEDIAPIPE_MODEL = REPO_ROOT / "models" / "mediapipe" / "face_landmarker.task"


def test_fake_detector_list_script() -> None:
    detection = FaceDetection(BBox(0.4, 0.3, 0.2, 0.2), None, 1.0, "fake")
    detector = FakeDetector([[detection], []])
    frame = make_frame()
    assert detector.detect(frame) == [detection]
    assert detector.detect(frame) == []
    assert detector.calls == 2


def test_select_primary_largest() -> None:
    small = FaceDetection(BBox(0.1, 0.1, 0.1, 0.1), None, 1.0, "x")
    large = FaceDetection(BBox(0.3, 0.3, 0.3, 0.3), None, 1.0, "y")
    assert select_primary([small, large])[0] is large


def test_yunet_missing_model_raises(tmp_path: Path) -> None:
    with pytest.raises(ModelNotFoundError):
        YuNetDetector(tmp_path / "missing.onnx")


@pytest.mark.model
def test_yunet_real_image() -> None:
    import cv2

    if not YUNET_MODEL.exists():
        pytest.skip("YuNet model not downloaded")
    image = cv2.imread(str(ASTRONAUT), cv2.IMREAD_COLOR)
    assert image is not None
    detector = YuNetDetector(YUNET_MODEL)
    try:
        detections = detector.detect(Frame(image=image, timestamp=0.0, index=0, source="test"))
    finally:
        detector.close()
    assert len(detections) == 1
    assert detections[0].score > 0.8
    assert 0 < detections[0].bbox.cx < 1


@pytest.mark.mediapipe
def test_mediapipe_real_image() -> None:
    import cv2

    from avfm.detection.mediapipe import MediaPipeDetector
    from avfm.metrics.ear import compute_ear

    if not MEDIAPIPE_MODEL.exists():
        pytest.skip("MediaPipe model not downloaded")
    image = cv2.imread(str(ASTRONAUT), cv2.IMREAD_COLOR)
    assert image is not None
    detector = MediaPipeDetector(MEDIAPIPE_MODEL, running_mode="IMAGE")
    try:
        detections = detector.detect(Frame(image=image, timestamp=0.0, index=0, source="test"))
    finally:
        detector.close()
    assert len(detections) == 1
    assert detections[0].landmarks is not None
    assert len(detections[0].landmarks) == 478
    ear = compute_ear(detections[0].landmarks, (image.shape[1], image.shape[0]))
    assert ear.valid
    assert ear.ear > 0.15
