from __future__ import annotations

import dataclasses

from avfm.app.simulation import GimbalPlant, Scenario, run_simulation
from avfm.config import AppConfig


def test_plant_first_order_step() -> None:
    plant = GimbalPlant(pan=90, tilt=80, tau_s=0.1, max_rate_deg_s=120)
    plant.step(100, 80, 0.1)
    assert 90 < plant.pan < 100


def test_step_scenario_settles(config: AppConfig) -> None:
    report = run_simulation(Scenario(name="step"), config, duration=12.0)
    assert report.settled
    assert report.final_error < 0.05
    assert report.overshoot < 0.25


def test_sine_scenario_tracks(config: AppConfig) -> None:
    report = run_simulation(Scenario(name="sine"), config, duration=12.0)
    assert report.rmse < 0.1
    assert report.max_error < 0.2


def test_lost_scenario_searches_and_reacquires(config: AppConfig) -> None:
    tracker = dataclasses.replace(config.tracker, lost_timeout_s=2.0, hold_last_s=0.2)
    lost_config = dataclasses.replace(config, tracker=tracker)
    report = run_simulation(
        Scenario(name="lost", lost_start=3.0, lost_duration=5.0),
        lost_config,
        duration=14.0,
    )
    assert report.search_started
    assert report.reacquire_time_s is not None
    assert report.face_lost_events >= 1
