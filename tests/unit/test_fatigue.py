from __future__ import annotations

import dataclasses

from avfm.config import FatigueConfig
from avfm.events import EventBus, ListEventSink
from avfm.fatigue.monitor import FatigueMonitor
from avfm.types import EventType, FatigueState
from tests.helpers import make_metrics


def monitor_config(**overrides):
    base = FatigueConfig(
        ear_threshold=0.2,
        closure_confirm_s=0.1,
        microsleep_s=1.0,
        blink_min_s=0.05,
        blink_max_s=0.3,
        perclos_window_s=10.0,
        perclos_warmup_s=5.0,
        perclos_threshold=0.2,
        perclos_min_coverage=0.5,
        perclos_max_gap_s=1.0,
        max_metrics_age_s=0.5,
        distraction_yaw_deg=20.0,
        distraction_pitch_deg=15.0,
        distraction_confirm_s=0.5,
        recovery_s=0.5,
        event_cooldown_s=0.0,
        face_lost_s=0.5,
    )
    return dataclasses.replace(base, **overrides)


def make_monitor(**overrides):
    sink = ListEventSink()
    monitor = FatigueMonitor(monitor_config(**overrides), event_bus=EventBus([sink]))
    return monitor, sink


def feed(
    monitor: FatigueMonitor,
    t: float,
    *,
    ear: float = 0.3,
    yaw: float = 0.0,
    pitch: float = 0.0,
    valid: bool = True,
):
    return monitor.update(
        make_metrics(
            ear=ear, yaw=yaw, pitch=pitch, valid_landmarks=valid, valid_pose=valid, timestamp=t
        ),
        t,
        detection_ran=True,
    )


def test_blink_is_not_microsleep() -> None:
    monitor, sink = make_monitor()
    feed(monitor, 0.0)
    feed(monitor, 0.1, ear=0.05)
    feed(monitor, 0.2, ear=0.05)
    snapshot = feed(monitor, 0.3)
    assert snapshot.state == FatigueState.ALERT
    assert any(event.type == EventType.BLINK for event in sink.events)
    assert snapshot.blink_rate >= 1.0


def test_microsleep_triggers_drowsy_and_recovers() -> None:
    monitor, sink = make_monitor()
    feed(monitor, 0.0)
    feed(monitor, 0.1, ear=0.05)
    snapshot = feed(monitor, 1.2, ear=0.05)
    assert snapshot.state == FatigueState.DROWSY
    assert any(event.type == EventType.DROWSY_STARTED for event in sink.events)
    feed(monitor, 1.3)
    snapshot = feed(monitor, 2.4)
    assert snapshot.state == FatigueState.ALERT
    assert any(event.type == EventType.DROWSY_ENDED for event in sink.events)


def test_perclos_can_trigger_drowsy() -> None:
    monitor, sink = make_monitor(microsleep_s=100.0, perclos_window_s=2.0, perclos_warmup_s=1.0)
    for index in range(11):
        feed(monitor, index * 0.1, ear=0.05)
    for index in range(11, 22):
        feed(monitor, index * 0.1, ear=0.3)
    snapshot = feed(monitor, 2.2)
    assert snapshot.perclos_ready
    assert snapshot.perclos >= 0.2
    assert snapshot.state == FatigueState.DROWSY
    assert any(event.type == EventType.DROWSY_STARTED for event in sink.events)


def test_looking_away_distraction() -> None:
    monitor, sink = make_monitor(microsleep_s=100.0, perclos_warmup_s=10.0)
    feed(monitor, 0.0, yaw=30.0, pitch=0.0)
    snapshot = feed(monitor, 0.6, yaw=30.0, pitch=0.0)
    assert snapshot.state == FatigueState.DISTRACTED
    assert any(event.type == EventType.DISTRACTED_STARTED for event in sink.events)
    feed(monitor, 0.7, yaw=0.0)
    snapshot = feed(monitor, 1.2, yaw=0.0)
    assert snapshot.state == FatigueState.ALERT
    assert any(event.type == EventType.DISTRACTED_ENDED for event in sink.events)


def test_pose_gating_rejects_ear() -> None:
    monitor, _ = make_monitor(microsleep_s=100.0, perclos_warmup_s=10.0)
    feed(monitor, 0.0, ear=0.05, yaw=30.0)
    snapshot = feed(monitor, 0.6, ear=0.05, yaw=30.0)
    assert snapshot.ear == 0.0
    assert not snapshot.eyes_closed
    assert snapshot.state == FatigueState.DISTRACTED


def test_no_face_state() -> None:
    monitor, _ = make_monitor()
    feed(monitor, 0.0)
    snapshot = monitor.update(None, 1.5, detection_ran=True)
    assert snapshot.state == FatigueState.NO_FACE
    assert snapshot.reason == "no_face"


def test_unavailable_monitor() -> None:
    monitor = FatigueMonitor(monitor_config(), available=False)
    snapshot = monitor.update(None, 1.0, detection_ran=False)
    assert snapshot.state == FatigueState.UNAVAILABLE


def test_reset() -> None:
    monitor, _ = make_monitor()
    feed(monitor, 0.0, ear=0.05)
    monitor.reset()
    snapshot = monitor.update(None, 0.0, detection_ran=False)
    assert snapshot.state == FatigueState.NO_FACE
