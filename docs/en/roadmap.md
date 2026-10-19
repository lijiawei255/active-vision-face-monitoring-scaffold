# Roadmap

## v0.1.x

- Raspberry Pi HIL run: `scripts/rpi_smoke.py`, `scripts/rpi_bench.py`, publish actual numbers.
- Fix issues found on real Picamera2/PCA9685 hardware.
- Add HIL result reports under `docs/en/`/`docs/zh/`.

## v0.2

- Optional serial servo backend for ESP32/STM32 with a documented line protocol and example
  firmware.
- Yawn detection (MAR) and gaze/iris indicators.
- Better multi-face selection and optional face tracking by ID.
- Camera calibration helper for `fx/fy/cx/cy`.

## v0.3+

- ONNX detector alternatives and performance comparisons.
- MkDocs/GitHub Pages documentation site.
- PyPI publication (`avfm` name is currently available).
- Optional Docker/headless deployment notes.
- CodeQL/OpenSSF Scorecard and release automation.

## Explicit non-goals

- Face recognition/identity.
- Medical or safety certification.
- Cloud upload or a hosted dashboard.
- A turnkey end-user application.
