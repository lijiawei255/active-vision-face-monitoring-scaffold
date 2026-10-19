from __future__ import annotations

import json
from pathlib import Path

import pytest

from avfm.cli import main

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_info_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["info", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["version"]
    assert "models" in data


def test_dry_run_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--dry-run", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["detector"]["mode"] in {"single", "split"}


def test_replay_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    session = tmp_path / "session.jsonl"
    session.write_text(
        json.dumps(
            {
                "type": "observation",
                "t": 0.0,
                "frame_size": [640, 480],
                "bbox": [0.4, 0.3, 0.2, 0.2],
                "score": 1.0,
                "detector": "test",
            }
        ),
        encoding="utf-8",
    )
    assert main(["replay", "--input", str(session), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["observations"] == 1


def test_doctor_strict(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor", "--json", "--strict"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
