# Performance

## Prior evidence from the parent project

The parent project (`BJTU_Desktop-Learing-Assistant`) was tested on a Raspberry Pi 5:

- final configuration: 640×480 @ 15 fps;
- `face_detection_interval = 1` (Haar every frame);
- `distraction_interval_frames = 2` (MediaPipe every 2 frames, 7.5 Hz);
- tracking and distraction detection were reported as timely and accurate after tuning;
- the initial MediaPipe implementation stuttered, and was fixed by frame skipping/lower sampling.

Earlier documentation also records a lower-load profile: Haar every 3 frames (5 Hz) and MediaPipe
every 5 frames. The final commit moved to the denser cadence after measurement.

This is **evidence about the parent implementation**, not a verification of this repository's new
code. The new code uses YuNet instead of Haar and MediaPipe Tasks instead of the legacy Solutions
API, so it must be benchmarked again on hardware.

## New profiles

| Profile | Resolution/FPS | Tracking | Fatigue | Intent |
|---|---|---|---|---|
| `desktop` | 640×480 @ 15 | single detector, every frame | same | Windows laptop |
| `rpi` | 640×480 @ 15 | YuNet every frame | MediaPipe every 2 frames | default Pi |
| `rpi_low_power` | 480×360 @ 10 | YuNet every 2 frames | MediaPipe every 3 frames | heat/throttling |
| `rpi_passive` | 640×480 @ 15 | YuNet every frame | MediaPipe every 2 frames | Pi camera, no servos |
| `rpi_tracking_only` | 640×480 @ 15 | YuNet every frame | disabled | no MediaPipe |

Cadence is configurable:

```toml
[detector]
mode = "split"
tracking_backend = "yunet"
fatigue_backend = "mediapipe"
tracking_interval_frames = 1
fatigue_interval_frames = 2
```

## Metrics

`run.json` records:

- `loop_fps`, `tracking_hz`, `fatigue_hz`;
- `avg_loop_ms`, `p95_loop_ms`;
- `avg_tracking_detect_ms`, `avg_fatigue_detect_ms`;
- `dropped_frames`, `errors`.

The first frame includes model initialization and is not representative; use
`scripts/rpi_bench.py` (which discards warm-up) for HIL numbers.

## Measured on the Windows development laptop (v0.1.2)

| Item | Result |
|---|---|
| Python / OpenCV / MediaPipe | 3.11.17 / 5.0.0 / 1.1.1 |
| Core tests | 236 passed; 89% coverage |
| YuNet on `tests/data/astronaut.jpg` | 1 face, score 0.932 |
| MediaPipe on same image | 1 face, 478 landmarks, EAR 0.308, yaw 34.2°, pitch 5.6°, roll 11.7° |
| Webcam passive run (5 s) | 58 frames, ~11.5 fps, avg loop ~15.9 ms |
| Annotated video (3 s) | 30 frames, `annotated.mp4` written |
| `avfm selftest` | step settled 0.53 s, overshoot 0.022; sine RMSE 0.088; lost search/re-acquire reported |

No face was guaranteed in front of the webcam during the automated run; detector accuracy is
covered by the public-domain image test. Real-face webcam tracking is a manual smoke test.

## Pi 5 HIL procedure

When hardware is available:

```bash
conda run -n avfm python scripts/rpi_bench.py --profile rpi --duration 30 --json var/bench_rpi.json
conda run -n avfm python scripts/rpi_bench.py --profile rpi_low_power --duration 30
conda run -n avfm python scripts/rpi_bench.py --profile tracking_only --duration 30
```

Targets (starting points, not guarantees):

- control loop ≥ 10 fps;
- tracking detection ≥ 10 Hz;
- fatigue sampling ≥ 5 Hz;
- no visible stutter, stable tracking, no thermal throttling.

If the `rpi` profile misses the targets, use `rpi_low_power` or `rpi_tracking_only`; record the
actual numbers in this document and the README verification matrix.
