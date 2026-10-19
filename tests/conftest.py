"""Pytest configuration and shared fixtures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from avfm.config import load_config
from avfm.types import Frame

REPO_ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-webcam", action="store_true", help="Enable local webcam tests")
    parser.addoption(
        "--run-hardware", action="store_true", help="Enable Raspberry Pi hardware tests"
    )
    parser.addoption("--run-mediapipe", action="store_true", help="Enable MediaPipe model tests")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        for marker, option in (
            ("webcam", "--run-webcam"),
            ("hardware", "--run-hardware"),
            ("mediapipe", "--run-mediapipe"),
        ):
            if item.get_closest_marker(marker) and not config.getoption(option):
                item.add_marker(pytest.mark.skip(reason=f"requires explicit {option}"))


@pytest.fixture
def config(tmp_path: Path):
    return load_config(cwd=tmp_path)


@pytest.fixture
def frame() -> Frame:
    return Frame(
        image=np.zeros((480, 640, 3), dtype=np.uint8),
        timestamp=0.0,
        index=0,
        source="test",
    )
