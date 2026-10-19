# 移植指南

## 替换相机

实现 `avfm.capture.base.FrameSource`：

```python
class MySource(FrameSource):
    def open(self): ...
    def read(self) -> Frame | None: ...  # BGR uint8，单调时间戳
    def close(self): ...
    @property
    def description(self) -> str: ...
```

然后直接交给 `Runner.run(source, pipeline)`，或在你自己的应用里加工厂。保持 BGR 契约和单调时间戳。

## 替换检测器

实现 `avfm.detection.base.FaceDetector`：

```python
class MyDetector(FaceDetector):
    name = "my-detector"
    supports_landmarks = True

    def detect(self, frame: Frame) -> list[FaceDetection]: ...
    def close(self): ...
```

返回归一化 `BBox`；模型有关键点就返回关键点。EAR/头部姿态默认使用 MediaPipe 478 点索引，
所以要么把关键点映射到这些索引，要么自己实现 metrics。

## 替换执行器

实现 `avfm.actuation.base.Servo`（`set_angle`、`get_angle`、`close`）。如果执行器真的会转动相机，
通过 `ActuatorCapabilities` 设置 `can_move=True`/`physical=True`，tracker 才会启用物理扫描。
串口 ESP32/STM32 后端是路线图项；接入点见 `examples/custom_servo.py`。

## 保持测试诚实

- 为新 backend 加伪传输的契约测试。
- 为新控制路径加 SIL 或回放测试。
- 在 `scripts/rpi_smoke.py`/`rpi_bench.py` 真正跑过之前，不要把硬件标成已验证。
- 同时更新 `docs/en` 和 `docs/zh`。
