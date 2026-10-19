# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versioning follows
[Semantic Versioning](https://semver.org/).

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
