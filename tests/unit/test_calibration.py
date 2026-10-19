from __future__ import annotations

import json
from pathlib import Path

import pytest

from avfm.fatigue.calibration import EarCalibration


def test_calibration_from_samples() -> None:
    calibration = EarCalibration.from_samples([0.3] * 20)
    assert calibration.baseline == pytest.approx(0.3)
    assert calibration.threshold == pytest.approx(0.21)
    assert calibration.samples == 20


def test_calibration_floor_and_ceiling() -> None:
    assert EarCalibration.from_samples([0.1] * 20).threshold == pytest.approx(0.15)
    assert EarCalibration.from_samples([0.5] * 20).threshold == pytest.approx(0.25)


def test_calibration_too_few_samples() -> None:
    with pytest.raises(ValueError):
        EarCalibration.from_samples([0.3] * 2, min_samples=10)


def test_calibration_roundtrip(tmp_path: Path) -> None:
    calibration = EarCalibration.from_samples([0.28] * 20, source="webcam:0", frame_size=(640, 480))
    path = calibration.save(tmp_path / "calibration.json")
    assert path.exists()
    loaded = EarCalibration.load(path)
    assert loaded == calibration
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["source"] == "webcam:0"
