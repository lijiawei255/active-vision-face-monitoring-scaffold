# Testing

## Test pyramid

| Layer | What | Hardware? | CI? |
|---|---|---|---|
| Unit | PID, gimbal, tracker, EAR, head pose, PERCLOS, state machine, config, models, calibration | no | yes |
| Contract | fake MediaPipe, fake Picamera2, fake ServoKit, detector cadence | no | yes |
| Real detector | YuNet/MediaPipe on the public-domain image | no | yes (models downloaded) |
| SIL | virtual gimbal plant + face trajectories + PID/search | no | yes |
| Integration | pipeline single/split/passive/mock, CLI, overlay, JSONL, replay | no | yes |
| Webcam | local camera capture and passive loop | camera | manual/opt-in |
| HIL | Picamera2 + PCA9685 + servos + benchmark | Pi | manual/opt-in |

## Commands

```bash
# Core suite (no webcam, no Pi hardware, no MediaPipe package requirement)
pytest -m "not webcam and not hardware and not mediapipe" \
  --cov=avfm --cov-fail-under=80

# Real model tests (MediaPipe also needs a working GL/EGL stack)
pytest -m "mediapipe or model" --run-mediapipe

# Local webcam
pytest -m webcam --run-webcam

# Raspberry Pi hardware
pytest -m hardware --run-hardware
```

Markers are registered in `pyproject.toml`:
`model`, `mediapipe`, `webcam`, `hardware`, `slow`.

## Static checks

The shipped `py.typed` marker is a contract: `src/` is type-checked in CI and pre-commit.

```bash
ruff check src tests
ruff format --check src tests
mypy          # src only; configuration lives in pyproject.toml
```

## Dependency locks

CI installs exact, hashed versions from `requirements/` instead of resolving ranges at build time.

| File | Used by |
|---|---|
| `lock-core.txt` | runtime dependencies only (wheel smoke test) |
| `lock-dev.txt` | lint, core tests, docs checks |
| `lock-dev-mediapipe.txt` | MediaPipe/model tests |

Regenerate all three after changing dependencies; the lint job fails if they drift.

```bash
uv pip compile pyproject.toml --universal --python-version 3.11 \
  --generate-hashes -o requirements/lock-core.txt
uv pip compile pyproject.toml --extra dev --universal --python-version 3.11 \
  --generate-hashes -o requirements/lock-dev.txt
uv pip compile pyproject.toml --extra dev --extra mediapipe --universal \
  --python-version 3.11 --generate-hashes -o requirements/lock-dev-mediapipe.txt
```

The `rpi` extra depends on Linux-only `picamera2`, so it is installed on the Pi with
`pip install -e ".[rpi]"` and is not part of the universal lock.

## SIL scenarios

`avfm simulate` and `scripts/rpi_bench.py` use a first-order pan/tilt plant and a projected face
position. The acceptance checks in `avfm selftest` are:

- step ±20°: settles, final error < 0.05, overshoot < 0.25;
- sine ±20°/8 s: RMSE < 0.1, max error < 0.2;
- lost 5 s: search starts; re-acquire time is reported;
- cadence: tracking/fatigue detectors called on the configured frame indices; PID runs every frame.

## Test fixture

`tests/data/astronaut.jpg` is a resized derivative of the scikit-image `astronaut` sample:

- NASA Great Images, public domain, no known copyright restrictions;
- subject: astronaut Eileen Collins;
- used only to verify detector/landmark extraction, never for identification or training.

See `tests/data/README.md`.

## HIL checklist (Raspberry Pi)

1. Power off; check external 5V, common ground and cable strain relief.
2. `libcamera-hello --list-cameras`; `sudo i2cdetect -y 1` shows `0x40`.
3. Run `avfm doctor --probe-camera --probe-actuator`.
4. Run passive mode first (`--servo none`), verify face detection/EAR/PERCLOS.
5. Sweep one servo at a time with small angles; confirm limits and direction.
6. Run active mode; keep an emergency stop ready.
7. Run `scripts/rpi_bench.py` for `rpi`, `rpi_low_power`, `tracking_only`; record results.
8. Run `scripts/rpi_smoke.py`; attach `var/hil_report.json` to the hardware report issue.

Do not report HIL results as passed until the script output exists.
