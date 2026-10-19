from __future__ import annotations

import json
from pathlib import Path

import pytest

from avfm.cli import main

REPO_ROOT = Path(__file__).resolve().parents[2]
ASTRONAUT = REPO_ROOT / "tests" / "data" / "astronaut.jpg"
YUNET_MODEL = REPO_ROOT / "models" / "yunet" / "face_detection_yunet_2026may.onnx"


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "avfm" in capsys.readouterr().out


def test_selftest_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["selftest", "--quick", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert all(data["checks"].values())


def test_simulate_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["simulate", "--scenario", "step", "--duration", "4", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["frames"] > 0


def test_doctor_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True


def test_models_verify_yunet(capsys: pytest.CaptureFixture[str]) -> None:
    if not YUNET_MODEL.exists():
        pytest.skip("YuNet model not downloaded")
    assert main(["models", "verify", "--only", "yunet", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["yunet"] is True


@pytest.mark.model
def test_detect_image(capsys: pytest.CaptureFixture[str]) -> None:
    if not YUNET_MODEL.exists():
        pytest.skip("YuNet model not downloaded")
    assert main(["detect", "--source", f"image:{ASTRONAUT}", "--detector", "yunet", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["detections"]) == 1


@pytest.mark.model
def test_run_image(capsys: pytest.CaptureFixture[str]) -> None:
    if not YUNET_MODEL.exists():
        pytest.skip("YuNet model not downloaded")
    assert (
        main(
            [
                "run",
                "--source",
                f"image:{ASTRONAUT}",
                "--detector",
                "yunet",
                "--servo",
                "none",
                "--no-show",
                "--max-frames",
                "1",
                "--json",
            ]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["frames"] == 1
