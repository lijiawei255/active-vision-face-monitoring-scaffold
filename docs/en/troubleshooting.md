# Troubleshooting

## Models

**`Model file not found` / `ModelVerificationError`**

```bash
avfm models download --all
# or
avfm models download --only yunet
avfm models download --only mediapipe
avfm models verify --all
```

Use `--force` only if the existing file is corrupt. Check `AVFM_MODEL_DIR` / `--model-dir` if you
store models elsewhere.

## MediaPipe

**`mediapipe is not installed`**

```bash
pip install -e ".[mediapipe]"
```

On Raspberry Pi, MediaPipe is optional. If it cannot be installed, use
`configs/rpi_tracking_only.toml` or `--detector yunet`; fatigue will be reported as unavailable.

**`module 'mediapipe' has no attribute 'solutions'`**

That API was removed in MediaPipe 0.10.31+. This project uses `mp.tasks`; do not use
`mp.solutions`.

## OpenCV

**`cv2.CascadeClassifier` missing / `haarcascades` empty**

OpenCV 5 moved Haar/HOG to contrib and the pip wheels do not ship the XMLs. This project uses
YuNet (`cv2.FaceDetectorYN`) and does not need Haar.

**OpenCV import fails on Linux**

Install the GUI/GL runtime libraries:

```bash
sudo apt install -y libgl1 libglib2.0-0
```

## Camera

- Windows: check Camera privacy settings and close other apps using the camera.
- Pi: `libcamera-hello --list-cameras`; ensure the CSI cable is seated; check `video` group
  permissions.
- If the camera returns frames but no face is detected, check lighting, distance (roughly
  0.3–2 m), and that the model was downloaded.
- `--show` on a headless Pi: use `--no-show` and `--record-video` instead.

## I2C / PCA9685

**`PCA9685 not found at I2C address 0x40`**

```bash
sudo i2cdetect -y 1
```

Check SDA/SCL, common ground, external 5V and the address jumpers. Use `--servo none` until the
bus is visible. For `--servo auto`, a failed probe falls back to passive mode with a warning.

## Servo direction / jitter

- Use `tracker.invert_pan` / `tracker.invert_tilt` for mounting direction.
- Reduce `kp` / `output_limit` if the servo buzzes or oscillates.
- Increase `tracker.deadband_x/y` slightly if the camera hunts around the centre.
- Ensure the external supply can deliver the stall current of both servos.

## Performance / stutter

- Use `configs/rpi_low_power.toml` or reduce `runtime.fps`, resolution, and detector cadence.
- Use `--detector yunet` for tracking-only.
- Run `scripts/rpi_bench.py` and compare `loop_fps`, `avg_loop_ms`, `p95_loop_ms`.
- Ensure cooling; check `vcgencmd measure_temp`.

## Tests

- `--run-webcam`, `--run-hardware`, `--run-mediapipe` are required for opt-in tests.
- Model tests are skipped when models are missing; run `avfm models download --all` first.
- On Linux, set `MPLBACKEND=Agg` if a transitive dependency tries to open a display.
