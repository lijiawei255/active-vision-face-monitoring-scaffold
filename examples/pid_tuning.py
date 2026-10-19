"""Compare PID gains in the SIL plant (no hardware)."""

from __future__ import annotations

import dataclasses

from avfm.app.simulation import Scenario, run_simulation
from avfm.config import load_config


def main() -> None:
    base = load_config()
    for kp in (60.0, 100.0, 120.0, 140.0):
        tracker = dataclasses.replace(
            base.tracker,
            pan_pid=dataclasses.replace(base.tracker.pan_pid, kp=kp),
            tilt_pid=dataclasses.replace(base.tracker.tilt_pid, kp=kp * 0.8),
        )
        config = dataclasses.replace(base, tracker=tracker)
        step = run_simulation(Scenario(name="step"), config, duration=12.0)
        sine = run_simulation(Scenario(name="sine"), config, duration=12.0)
        print(
            f"kp={kp:5.1f}  step settled={step.settled} "
            f"final={step.final_error:.3f}  sine_rmse={sine.rmse:.3f}"
        )


if __name__ == "__main__":
    main()
