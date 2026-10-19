# Porting guide

## Replacing the camera

Implement `avfm.capture.base.FrameSource`:

```python
class MySource(FrameSource):
    def open(self): ...
    def read(self) -> Frame | None: ...  # BGR uint8, monotonic timestamp
    def close(self): ...
    @property
    def description(self) -> str: ...
```

Then either use it directly with `Runner.run(source, pipeline)` or add a user-level factory in your
application. Keep the BGR contract and monotonic timestamps.

## Replacing the detector

Implement `avfm.detection.base.FaceDetector`:

```python
class MyDetector(FaceDetector):
    name = "my-detector"
    supports_landmarks = True

    def detect(self, frame: Frame) -> list[FaceDetection]: ...
    def close(self): ...
```

Return normalised `BBox`; return landmarks if your model provides them. EAR/head pose expect the
MediaPipe 478-point index layout, so either map your landmarks to those indices or provide a custom
metrics implementation.

## Replacing the actuator

Implement `avfm.actuation.base.Servo` (`set_angle`, `get_angle`, `close`). If your actuator moves the
camera, set `can_move=True`/`physical=True` through `ActuatorCapabilities` so the tracker enables
physical search. A serial ESP32/STM32 backend is a roadmap item; see
`examples/custom_servo.py` for the integration point.

## Keeping tests honest

- Add contract tests for the new backend with a fake transport.
- Add a SIL or replay test for the new control path.
- Do not mark hardware as verified until `scripts/rpi_smoke.py`/`rpi_bench.py` have run on it.
- Update both `docs/en` and `docs/zh`.
