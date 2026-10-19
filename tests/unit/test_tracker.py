from __future__ import annotations

import dataclasses

from avfm.config import AppConfig
from avfm.control.tracker import FaceTracker
from avfm.events import EventBus, ListEventSink
from avfm.types import EventType, TrackerState
from tests.helpers import make_observation


def make_tracker(config: AppConfig, *, can_actuate: bool = True):
    sink = ListEventSink()
    tracker_config = dataclasses.replace(config.tracker, hold_last_s=0.1, lost_timeout_s=0.2)
    tracker = FaceTracker(
        tracker_config,
        config.gimbal,
        can_actuate=can_actuate,
        event_bus=EventBus([sink]),
    )
    return tracker, sink


def test_acquire_hold_and_lose(config: AppConfig) -> None:
    tracker, sink = make_tracker(config)
    observation = make_observation(timestamp=0.0)
    result = tracker.update(observation, 0.0)
    assert result.state == TrackerState.TRACKING
    assert any(event.type == EventType.FACE_ACQUIRED for event in sink.events)

    result = tracker.update(None, 0.05)
    assert result.state == TrackerState.TRACKING
    assert result.bbox is not None

    result = tracker.update(None, 0.2)
    assert result.state in {TrackerState.FACE_LOST, TrackerState.SEARCHING}
    assert any(event.type == EventType.FACE_LOST for event in sink.events)


def test_active_mode_starts_search_and_reacquires(config: AppConfig) -> None:
    tracker, sink = make_tracker(config, can_actuate=True)
    tracker.update(make_observation(timestamp=0.0), 0.0)
    result = tracker.update(None, 0.2)
    assert result.state == TrackerState.SEARCHING
    assert any(event.type == EventType.SEARCH_STARTED for event in sink.events)
    assert result.command.reason == "search"
    result = tracker.update(make_observation(timestamp=1.0), 1.0)
    assert result.state == TrackerState.TRACKING
    assert any(event.type == EventType.FACE_ACQUIRED for event in sink.events)


def test_passive_mode_does_not_search(config: AppConfig) -> None:
    tracker, sink = make_tracker(config, can_actuate=False)
    tracker.update(make_observation(timestamp=0.0), 0.0)
    result = tracker.update(None, 0.2)
    assert result.state == TrackerState.FACE_LOST
    assert not any(event.type == EventType.SEARCH_STARTED for event in sink.events)
    assert result.command.reason == "hold"


def test_park(config: AppConfig) -> None:
    tracker, _ = make_tracker(config)
    tracker.update(make_observation(timestamp=0.0), 0.0)
    command = tracker.park(0.1)
    assert command.reason == "park"
    assert tracker.state == TrackerState.IDLE
