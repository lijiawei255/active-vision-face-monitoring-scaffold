# Control design

## PID form

Each axis uses a velocity-form PID:

```text
error e = normalised face offset (positive = right/below)
integral I += e * dt            (clamped)
derivative D = (e - e_prev) / dt
output u = Kp*e + Ki*I + Kd*D   (clamped to ±output_limit, deg/s)
angle += sign * u * dt          (clamped to ±max_step_deg and mechanical limits)
```

- `output_limit` is in **deg/s**, not degrees.
- `integral_limit` is in error·seconds; conditional integration freezes the integral when the
  output saturates in the same direction as the error.
- Inside the deadband the output is zero and the integral decays with `integral_decay`; this
  prevents a jump when the face re-enters the active region.
- `max_step_deg` is a final safety clamp for a single update.
- `invert_pan` / `invert_tilt` adapt the sign to the mechanical mounting.

## Defaults and tuning

The repository defaults were tuned in the SIL plant:

```toml
[tracker]
deadband_x = 0.03
deadband_y = 0.03

[tracker.pan_pid]
kp = 120.0
ki = 5.0
kd = 1.2
output_limit = 240.0

[tracker.tilt_pid]
kp = 100.0
ki = 5.0
kd = 1.0
output_limit = 200.0

[gimbal]
max_step_deg = 10.0
```

These are starting points, not universal gains. Tune with:

```bash
avfm simulate --scenario step --duration 12
avfm simulate --scenario sine --duration 12
```

Acceptance used by `avfm selftest`:

- step: settles, final normalised error < 0.05, overshoot < 0.25;
- sine (±20°, 8 s period): RMSE < 0.1, max error < 0.2;
- lost: search starts and re-acquire time is reported.

## Tracking state machine

```text
IDLE --face--> TRACKING --lost TTL--> FACE_LOST
FACE_LOST --lost_timeout & can_actuate--> SEARCHING
SEARCHING --face--> TRACKING (PID reset, FACE_ACQUIRED)
SEARCHING --max_cycles--> IDLE (park)
```

`can_actuate` is false for `none` and (by default) `mock`, so passive mode never performs a
physical search. The observation filter keeps the last bbox for `hold_last_s` to bridge missed
detections; after that the face is considered lost.

## Why the PID runs every frame

The detector may be slower than the camera (especially MediaPipe on a Pi). The tracker and PID run
at camera rate using the last observation within its TTL. This keeps the control signal smooth and
decouples control latency from detector latency.

## Feed-forward / future work

The current controller is pure feedback. A future version could use camera FOV and the face offset
to compute a feed-forward angular velocity, or estimate face depth/velocity with a filter. Those
are roadmap items; the SIL plant is the right place to evaluate them.
