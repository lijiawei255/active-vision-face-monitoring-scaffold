"""Discrete velocity-form PID with anti-windup and deadband handling."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from avfm.config import PIDConfig


@dataclass
class PIDAxis:
    """PID output is degrees/second; ``error`` is normalised to [-1, 1]."""

    config: PIDConfig
    integral: float = 0.0
    prev_error: float = 0.0
    last_output: float = 0.0
    initialized: bool = field(default=False, init=False)

    def update(self, error: float, dt: float) -> float:
        if dt <= 0 or not math.isfinite(error):
            return 0.0

        error = float(error)
        if abs(error) <= self.config.deadband:
            # Leak the integral instead of freezing it; this avoids a jump
            # when the face leaves the deadband after a long pause.
            self.integral *= math.exp(-self.config.integral_decay * dt)
            self.prev_error = error
            self.last_output = 0.0
            return 0.0

        derivative = (error - self.prev_error) / dt if self.initialized else 0.0
        candidate = self.integral + error * dt
        candidate = max(-self.config.integral_limit, min(self.config.integral_limit, candidate))

        output = self.config.kp * error + self.config.ki * candidate + self.config.kd * derivative
        # Conditional integration: do not wind up when the output is saturated
        # and the error is pushing further into the same direction.
        if abs(output) > self.config.output_limit and output * error > 0:
            candidate = self.integral
            output = (
                self.config.kp * error + self.config.ki * candidate + self.config.kd * derivative
            )

        self.integral = candidate
        self.prev_error = error
        self.initialized = True
        self.last_output = max(-self.config.output_limit, min(self.config.output_limit, output))
        return self.last_output

    def reset(self) -> None:
        self.integral = 0.0
        self.prev_error = 0.0
        self.last_output = 0.0
        self.initialized = False
