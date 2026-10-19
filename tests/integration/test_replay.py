from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from avfm.app.replay import load_session, replay_session
from avfm.config import AppConfig
from tests.helpers import make_metrics


def test_replay_session(tmp_path: Path, config: AppConfig) -> None:
    path = tmp_path / "session.jsonl"
    records = [
        {
            "type": "observation",
            "t": 0.0,
            "frame_size": [640, 480],
            "bbox": [0.4, 0.3, 0.2, 0.2],
            "score": 1.0,
            "detector": "test",
            "metrics": dataclasses.asdict(make_metrics(timestamp=0.0)),
        },
        {
            "type": "command",
            "t": 0.0,
            "pan": 95.0,
            "tilt": 80.0,
            "pan_rate": 1.0,
            "tilt_rate": 0.0,
            "applied": True,
            "reason": "track",
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    assert len(load_session(path)) == 2
    report = replay_session(path, config, compare=True)
    assert report["observations"] == 1
    assert len(report["commands"]) == 1
    assert "compare" in report
    assert report["compare"]["recorded_commands"] == 1
