# Models

Models are **not committed** to this repository. Download and verify them with:

```bash
avfm models download --all
avfm models verify --all
```

| Model | File | License |
|---|---|---|
| YuNet face detector | `models/yunet/face_detection_yunet_2026may.onnx` | MIT (Shiqi Yu) |
| MediaPipe Face Landmarker | `models/mediapipe/face_landmarker.task` | Apache-2.0 |

Pinned URLs and SHA-256 are in `src/avfm/models.py` and
[`docs/en/architecture.md`](../docs/en/architecture.md#models). `models/*.onnx` and
`models/*.task` are gitignored.

On Raspberry Pi, `avfm doctor --strict` tells you which model is required by the selected profile.
