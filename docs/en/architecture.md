# Architecture

## Layers

```text
capture/      FrameSource: OpenCV (webcam/video/image), Picamera2
detection/    FaceDetector: YuNet, MediaPipe Face Landmarker, fake
perception/   single/split cadence, detector reuse, timing
metrics/      camera model, EAR, head pose (solvePnP)
fatigue/      PERCLOS window, EAR calibration, state machine
control/      PID axis, gimbal controller, observation filter, search, tracker
actuation/    Servo protocol, null/mock/PCA9685, gimbal safety
app/          Pipeline, Runner, Overlay, Recorder, Replay, Simulation
cli.py        avfm subcommands
```

The pipeline is single-threaded. A frame is read, perceived, tracked, fatigue-analysed, actuated
and optionally recorded before the next frame. This keeps latency and state deterministic and
makes replay possible.

## Data flow

```text
FrameSource.read() -> Frame(BGR, timestamp, frame_size)
Perception.process(frame, index) -> tracking_obs, fatigue_obs, ran flags, detect ms
compute_face_metrics(fatigue_obs) -> FaceMetrics(EAR, yaw/pitch/roll, validity)
FaceTracker.update(tracking_obs, t) -> TrackerResult(state, command, bbox, events)
FatigueMonitor.update(metrics, t, detection_ran) -> FatigueSnapshot + events
GimbalActuator.apply(command) -> applied / degraded
Overlay / JsonlRecorder / VideoRecorder / RunReport
```

## Contracts

- `Frame.image`: BGR `uint8`, shape `(H, W, 3)`.
- `BBox`: normalised `[0,1]`, origin top-left, positive width/height.
- Tracker error: `ex = 2 * (cx - 0.5)`, `ey = 2 * (cy - 0.5)`.
- PID output: degrees/second. `dt` is seconds and is clamped to `[0, 1]`.
- Angles: degrees. Pan/tilt limits are configured and clamped by both controller and actuator.
- Timestamps: monotonic seconds. Video uses `index / file_fps`; webcam uses a monotonic clock.
- EAR is computed in pixel space so non-square normalised coordinates do not distort the ratio.

## Detection cadence

- **single**: one detector, every `detector.interval_frames` frames.
- **split**: `tracking_detector` every `tracking_interval_frames`; `fatigue_detector` every
  `fatigue_interval_frames`. If both point at the same object, the detector is invoked once and
  the result is reused.
- The tracker runs every frame using the last observation within `tracker.hold_last_s`.
- PERCLOS samples are added only when the fatigue detector actually ran; skipped frames are not
  treated as "eyes open".

Default Pi profile: YuNet every frame + MediaPipe every 2 frames. Desktop profile: a single
MediaPipe detector every frame.

## Models

Models are not committed. `avfm models download` writes them under `models/` (or `--model-dir` /
`AVFM_MODEL_DIR`) and verifies SHA-256.

| Model | URL | SHA-256 | Size | License |
|---|---|---|---:|---|
| YuNet `face_detection_yunet_2026may.onnx` | `https://media.githubusercontent.com/media/opencv/opencv_zoo/26cc381e4d2594bb9f47a26eb8fd96c94a13660d/models/face_detection_yunet/face_detection_yunet_2026may.onnx` | `ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0` | 229,738 B | MIT (Shiqi Yu) |
| MediaPipe Face Landmarker `face_landmarker.task` | `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task` | `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff` | 3,758,596 B | Apache-2.0 |

Why not Haar: OpenCV 5 moved Haar/HOG to contrib and the pip wheels no longer ship
`cv2.data/haarcascades` (opencv-python issue #1244). Why not `mp.solutions`: MediaPipe 0.10.31+
removed the legacy Solutions API.

## Session format

`var/runs/<timestamp>/run.json` contains the resolved config, source/detector/actuator, versions,
start/end time and the `RunReport` performance counters.

`session.jsonl` contains records with a `type` field:

- `observation`: timestamp, frame size, bbox, score, detector, metrics;
- `command`: pan, tilt, rates, applied, reason;
- `fatigue`: state, EAR, PERCLOS/coverage/readiness, pose, blink rate;
- `event`: event name, timestamp, payload.

No raw pixels are written. `--record-video` writes an annotated MP4 separately.

## Error handling

- `ConfigError`: invalid TOML value/range.
- `DependencyMissingError`: optional package missing, with install/apt hint.
- `ModelNotFoundError` / `ModelVerificationError`: missing or wrong model, with download command.
- `CameraError`: source cannot open or keeps returning no frames.
- `ActuatorError`: requested physical actuator could not be initialized.
- `auto` actuator and detector fallbacks are logged, written to `run.json`, and visible in
  `doctor`; they are never silent.
