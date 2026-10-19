# Third-party licenses and notices

This project is MIT-licensed. It depends on the following packages/models; they are installed by
the package manager or downloaded at runtime and are not vendored here.

## Direct runtime dependencies

| Component | License | Link |
|---|---|---|
| OpenCV / opencv-contrib-python | Apache-2.0 | https://github.com/opencv/opencv |
| NumPy | BSD-3-Clause | https://numpy.org/ |

## Optional runtime dependencies

| Component | License | Link |
|---|---|---|
| MediaPipe | Apache-2.0 | https://github.com/google-ai-edge/mediapipe |
| Picamera2 | BSD-2-Clause | https://github.com/raspberrypi/picamera2 |
| Adafruit CircuitPython ServoKit / Blinka | MIT | https://github.com/adafruit/Adafruit_CircuitPython_ServoKit |

## Models (downloaded, not committed)

| Model | License | Link |
|---|---|---|
| YuNet `face_detection_yunet_2026may.onnx` | MIT, Copyright (c) 2020 Shiqi Yu | https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet |
| MediaPipe Face Landmarker `face_landmarker.task` | Apache-2.0 | https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker |

The MediaPipe model bundle is provided by Google under Apache-2.0. "MediaPipe" is a trademark of
Google LLC. The YuNet model is provided by the OpenCV Zoo under MIT.

## Development dependencies

| Component | License |
|---|---|
| pytest, pytest-cov, pytest-timeout | MIT |
| ruff | MIT |
| pre-commit | MIT |
| build | MIT |
| twine | Apache-2.0 |

## Test fixture

`tests/data/astronaut.jpg` is a resized derivative of the scikit-image `astronaut` sample,
downloaded from NASA Great Images. The image is public domain with no known copyright
restrictions. Subject: astronaut Eileen Collins. See `tests/data/README.md`.

## No unlicensed code

No code was copied from the unlicensed prior-art projects listed in `docs/en/prior-art.md` and
`docs/zh/prior-art.md`. They are cited for ideas and comparison only.
