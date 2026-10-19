# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versioning follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `mypy` type checking for `src/avfm`, wired into CI, pre-commit and the `dev` extra. The
  shipped `py.typed` marker is now an enforced contract rather than a claim.
- Locked, hashed dependency files under `requirements/` (`lock-core.txt`, `lock-dev.txt`,
  `lock-dev-mediapipe.txt`) generated with uv. CI installs from them and fails if they drift.
- Configuration-validation and CLI branch tests; core coverage rose from 81% to 88%.
- The MediaPipe job now runs the real MediaPipe model tests (`--run-mediapipe`) on headless
  Linux with the EGL/GLES libraries installed.

### Changed

- CI installs dependencies with uv from the lock files instead of resolving ranges with pip on
  every run.
- The package job installs the built wheel against the locked runtime dependencies.
- README/docs report the current test count and coverage (240 passed, 88%).

### Fixed

- `avfm models download` sends the real package version in its `User-Agent` header instead of a
  hard-coded `avfm/0.1`.
- Removed unnecessary `# type: ignore` comments in the fatigue monitor and head pose; the EAR and
  pose guards now narrow `FaceMetrics | None` explicitly. The two remaining ignores (dynamic
  handler attributes in `logging.py`) are documented and verified necessary by `warn_unused_ignores`.
- Removed a fragile `assert` at the end of the model download retry loop.
- Removed the stale `!.env.example` exception from `.gitignore` (no such file is shipped).

## [0.1.2] - 2026-10-20

### Changed

- Restored the compact default HUD for normal desktop/passive use. The large demo typography and
  the demonstration-only `--overlay-scale` CLI switch were removed.
- `run.json` no longer records the absolute local `loaded_from` config paths; the rest of the
  resolved configuration is still present for reproducibility.
- Kept the information fixes from v0.1.1: actual camera FPS, `EAR --` for invalid samples,
  immediate `EYES CLOSED`, and the drowsiness cause.

## [0.1.1] - 2026-10-20

### Added

- `configs/demo_short.toml` for the 10/15-second demonstration workflow; it is never loaded by
  the normal profiles.
- `--overlay-scale` for readable mobile/demo annotations.
- Tests for video geometry/duration, camera cleanup, PCA9685 channel calibration, startup parking,
  and demo-profile isolation.

### Fixed

- Head-pose landmark mapping now uses the outer eye corners (33/263), matching the 3D model;
  the old inner-corner mapping produced a systematic ~50° yaw bias on real webcam input.
- Demo-only thresholds are isolated in `configs/demo_short.toml`; generic defaults remain
  60 s/30 s PERCLOS and 15°/20° pose thresholds. `configs/desktop.toml` carries the laptop-specific
  25°/25° pitch tolerances.
- Video writer is opened lazily from the first actual frame, so webcam/image/Picamera resolution
  changes no longer crop or stretch the recording. Timestamped frames are duplicated/skipped to
  preserve wall-clock duration.
- OpenCV video sources read the file FPS before touching capture properties and release the
  capture object on open failure.
- Picamera2 closes a partially started camera on configuration/start failure and accepts RGBA
  frames defensively.
- PCA9685 applies per-channel pulse-width calibration even when the ServoKit is shared, validates
  pulse/angle ranges, and cleans up a partially initialized pan/tilt pair. A movable gimbal is
  parked at its default pose before the first frame.
- Overlay labels now show actual camera FPS, `EAR --` for invalid samples, `EYES CLOSED`,
  `DROWSY` cause, and `TARGET PAN/TILT`.

## [0.1.0] - 2026-10-19

### Added

- Hardware-agnostic capture layer: OpenCV webcam/video/image, Picamera2.
- YuNet detector (`cv2.FaceDetectorYN`) and MediaPipe Face Landmarker (Tasks API).
- Single and split detection cadence (fast tracking detector + slower landmark detector).
- Velocity-form PID with dt, deadband, output/integral limits, anti-windup, max step.
- Observation EMA/TTL, face lost/re-acquire, configurable search sweep.
- Passive/no-servo mode as a first-class operating mode.
- EAR, blink, microsleep, rolling PERCLOS, head pose, pose-gated EAR and EAR calibration.
- Null/mock/PCA9685 actuation with explicit `auto` fallback and error degradation.
- Pipeline, runner, overlay, JSONL session recording, annotated video, replay and SIL simulation.
- CLI: `run`, `simulate`, `replay`, `detect`, `calibrate`, `doctor`, `selftest`, `models`, `info`.
- Config profiles for desktop, Pi, low-power, passive and tracking-only.
- Bilingual English/Chinese documentation, prior-art/provenance/compliance notes.
- Pytest suite (121 passing on Windows dev laptop, 81% core coverage), ruff, pre-commit and CI.

### Notes

- Raspberry Pi hardware (Picamera2 + PCA9685 + servos) is contract-tested and scripted but
  **not yet executed on physical hardware** in this repository.
- Models are downloaded from pinned URLs and verified with SHA-256; they are not committed.
