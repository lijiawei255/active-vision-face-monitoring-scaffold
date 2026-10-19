# Provenance

## Parent project

This repository extracts and rewrites the vision subsystem of:

- [BJTU_Desktop-Learing-Assistant](https://github.com/lijiawei255/BJTU_Desktop-Learing-Assistant)
- MIT License, Copyright (c) 2026 Jiawei Li
- vision-related source commit: [`bc270b0`](https://github.com/lijiawei255/BJTU_Desktop-Learing-Assistant/commit/bc270b0)
  ("camera frame flip + tracking stop + per-frame detection")
- latest parent commit at extraction time: `952cccf`

## Extracted concepts

From `src/devices/camera.py`, `src/devices/servo_controller.py`, `src/devices/servo_mock.py`,
`src/processes/vision_process.py`, `src/config.py` and the parent docs:

- PID pan/tilt face tracking with a dead zone and auto-scan;
- face-mesh EAR/head-pose distraction detection;
- PCA9685 + SG90 servo limits, camera flip, mock servo/camera;
- Pi 5 performance profile: 640×480@15 fps, tracking every frame, MediaPipe every 2 frames.

## Behavioural changes

| Parent behaviour | This scaffold |
|---|---|
| `mp.solutions.face_mesh` | MediaPipe Tasks `FaceLandmarker` + downloaded model |
| Haar cascade from `cv2.data.haarcascades` | YuNet `cv2.FaceDetectorYN` (OpenCV 5 has no Haar data in core pip wheels) |
| Pixel error × `0.05` magic gain | Velocity-form PID in deg/s with dt, limits, anti-windup, deadband |
| `set_angle()` sleeps up to 2 s | Non-blocking command; rate limiting in the controller |
| Global `config` singleton | Typed dataclasses + TOML profiles + validation |
| Last face box held indefinitely | Observation TTL (`hold_last_s`) |
| Frame-count thresholds | Time-based thresholds for blinks/microsleep/PERCLOS |
| Fixed EAR threshold | Optional per-user EAR calibration |
| No PERCLOS | Rolling PERCLOS with coverage/freshness |
| No passive mode | First-class passive/no-servo mode |
| No SIL/replay/CI | Virtual plant, JSONL replay, pytest, GitHub Actions |

## What was not copied

- No code from the unlicensed prior-art projects in [prior-art.md](prior-art.md).
- No API keys, `.env`, user face images, demo videos or personal data from the parent project.
- The parent's LLM/audio/phone-box/TOF/LED/IR/button modules are out of scope.

## License

MIT. The parent project is MIT, so the extraction/rewrite is compatible. Keep the original
copyright notice and this provenance note when redistributing.
