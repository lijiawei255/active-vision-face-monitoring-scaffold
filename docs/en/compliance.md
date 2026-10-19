# Compliance and licensing

## Project license

MIT — see [`LICENSE`](../../LICENSE). Copyright (c) 2026 Jiawei Li.

No license change from the parent project. MIT is compatible with all direct dependencies and
models used here.

## Third-party components

| Component | License | Distribution |
|---|---|---|
| OpenCV / `opencv-contrib-python` | Apache-2.0 | pip dependency |
| NumPy | BSD-3-Clause | pip dependency |
| MediaPipe | Apache-2.0 | optional pip dependency |
| MediaPipe Face Landmarker model | Apache-2.0 | downloaded by `avfm models download`, not committed |
| YuNet `face_detection_yunet_2026may.onnx` | MIT (Copyright (c) 2020 Shiqi Yu) | downloaded, not committed |
| Picamera2 | BSD-2-Clause | optional Pi dependency |
| Adafruit CircuitPython ServoKit / Blinka | MIT | optional Pi dependency |
| pytest / ruff / pre-commit / build | MIT | dev dependencies |
| twine | Apache-2.0 | dev dependency |
| NASA astronaut test image | Public domain (NASA Great Images, no known copyright restrictions) | committed as `tests/data/astronaut.jpg` with attribution |

Transitive dependencies retain their own licenses in the installed environment. See
[`THIRD_PARTY_LICENSES.md`](../../THIRD_PARTY_LICENSES.md) for links.

## No unlicensed code

The prior-art table lists projects without a license. They are referenced for ideas only; no code
was copied. MIT-licensed projects are cited, and this implementation is a rewrite.

## Privacy

- Runtime processing is local; no frames are uploaded.
- No face recognition, identity database or embeddings.
- Recording is off by default. `--record-video` is explicit; JSONL stores boxes/metrics/events
  but no pixels.
- Deployers monitoring people at work, in vehicles or in classrooms must comply with local law
  and obtain informed consent (GDPR, Australian Privacy Act, workplace surveillance rules, etc.).
- Do not commit personal face images or recordings to the repository. The only committed face
  image is the public-domain NASA test fixture.

## Safety

- Fatigue indicators are heuristic; this is not a medical device and not a certified
  driver-monitoring system.
- Do not use it for safety-critical decisions.
- Servo power, mechanical limits and emergency stop are the builder's responsibility.

## Trademarks

Raspberry Pi, MediaPipe and OpenCV are trademarks of their respective owners. This project uses
their names descriptively; it is not affiliated with or endorsed by them.

## Anaconda and CI

- `environment.yml` uses `conda-forge` only, not Anaconda's `defaults` channel.
- GitHub Actions uses `pip` and the standard Python setup, not Anaconda.
- CI has `contents: read` permission, no secrets, and no `pull_request_target`.

## Export

No controlled encryption or export-restricted components are included.
