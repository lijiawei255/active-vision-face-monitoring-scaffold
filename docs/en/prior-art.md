# Prior art and positioning

Snapshot: GitHub, 2026-10-19. Stars and licenses change; verify before reusing anything.

| Project | Stars | License | What it covers | Gap vs this scaffold |
|---|---:|---|---|---|
| [TianxingWu/face-tracking-pan-tilt-camera](https://github.com/TianxingWu/face-tracking-pan-tilt-camera) | 245 | MIT | PC OpenCV + STM32, 2-DOF face tracking, PD control, image-coordinate errors | no fatigue, no automated tests, STM32-specific |
| [e-candeloro/Driver-State-Detection](https://github.com/e-candeloro/Driver-State-Detection) | 157 | MIT | webcam DMS, MediaPipe Tasks, EAR/gaze/head pose/PERCLOS, tests | no gimbal/active vision; full app, not a scaffold |
| [akshaybahadur21/Drowsiness_Detection](https://github.com/akshaybahadur21/Drowsiness_Detection) | 548 | MIT | classic dlib EAR drowsiness demo | no gimbal, no tests |
| [pimoroni/PanTiltFacetracker](https://github.com/pimoroni/PanTiltFacetracker) | 50 | **none** | Pi PanTilt HAT face tracking | no fatigue/tests; do not copy code |
| [pageauc/face-track-demo](https://github.com/pageauc/face-track-demo) | 45 | **none** | Pi camera face/motion tracking, scanning | no fatigue/tests; do not copy code |
| [Tandon-A/Drowsiness-Detection-Mediapipe](https://github.com/Tandon-A/Drowsiness-Detection-Mediapipe) | 30 | MIT | MediaPipe + LSTM, subject calibration | no gimbal |
| [sahnimanas/Fatigue-Detection](https://github.com/sahnimanas/Fatigue-Detection) | 58 | **none** | PERCLOS drowsiness | no gimbal; do not copy code |
| [Quackieduckie/tracking-screen](https://github.com/Quackieduckie/tracking-screen) | 1 | **none** | MediaPipe pan-tilt + background scanning | no fatigue/tests; do not copy code |
| [astrix884/Anti-Sleep-Robot](https://github.com/astrix884/Anti-Sleep-Robot) | 0 | **none** | face tracking + drowsiness + ESP32 turret | toy, no tests/license |
| [luvmangla05/LumiTrack](https://github.com/luvmangla05/LumiTrack) | 0 | **none** | SIL PID gimbal platform, different domain | no license; reference only |
| PyImageSearch pan-tilt tutorial | — | unclear | PID + pan/tilt teaching | code license unclear; do not copy |

## What is missing in the ecosystem

- Fatigue-only projects: good detection demos/apps, but no active camera control.
- Tracking-only projects: many single-file demos, hardware-specific, no tests, sometimes no license.
- Combined projects: toys or unlicensed prototypes.
- Generic Python/CV scaffolds: no domain-specific control/fatigue contracts.

## This project's position

A **maintained, MIT-licensed, tested engineering scaffold** at the intersection of:

1. 2-DOF PID gimbal face tracking;
2. EAR/PERCLOS/head-pose fatigue indicators;
3. hardware abstraction (webcam/Pi camera, null/mock/PCA9685);
4. passive/no-servo operation;
5. SIL, replay, contract tests and CI;
6. a Raspberry Pi 5 reference backend and performance profiles.

The value is integration, testability and documentation — not a new detection algorithm.

## Reuse policy

- No code was copied from the unlicensed projects above. They are cited for ideas and comparison.
- MIT-licensed projects are cited; this implementation is a rewrite.
- The parent project is MIT and is credited in [provenance.md](provenance.md).
