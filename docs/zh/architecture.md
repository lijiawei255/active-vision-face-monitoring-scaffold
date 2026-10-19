# 架构

## 分层

```text
capture/      FrameSource：OpenCV（摄像头/视频/图片）、Picamera2
detection/    FaceDetector：YuNet、MediaPipe Face Landmarker、fake
perception/   single/split cadence、检测器复用、计时
metrics/      相机模型、EAR、头部姿态（solvePnP）
fatigue/      PERCLOS 窗口、EAR 校准、状态机
control/      PID axis、云台控制器、观测滤波、扫描、tracker
actuation/    Servo 协议、null/mock/PCA9685、云台安全
app/          Pipeline、Runner、Overlay、Recorder、Replay、Simulation
cli.py        avfm 子命令
```

流水线是单线程的：读帧 → 感知 → 跟踪 → 疲劳 → 执行器 → 记录，然后下一帧。这样延迟和状态确定，
也便于回放。

## 数据流

```text
FrameSource.read() -> Frame(BGR, timestamp, frame_size)
Perception.process(frame, index) -> tracking_obs, fatigue_obs, ran flags, detect ms
compute_face_metrics(fatigue_obs) -> FaceMetrics(EAR, yaw/pitch/roll, validity)
FaceTracker.update(tracking_obs, t) -> TrackerResult(state, command, bbox, events)
FatigueMonitor.update(metrics, t, detection_ran) -> FatigueSnapshot + events
GimbalActuator.apply(command) -> applied / degraded
Overlay / JsonlRecorder / VideoRecorder / RunReport
```

## 契约

- `Frame.image`：BGR `uint8`，形状 `(H, W, 3)`。
- `BBox`：归一化 `[0,1]`，原点左上，宽高为正。
- 跟踪误差：`ex = 2 * (cx - 0.5)`，`ey = 2 * (cy - 0.5)`。
- PID 输出：°/s；`dt` 单位为秒，钳位到 `[0, 1]`。
- 角度单位为度；控制器和执行器都会做限位钳位。
- 时间戳单调递增（秒）。视频用 `index / file_fps`；摄像头用单调时钟。
- EAR 在像素空间计算，避免非等比归一化破坏纵横比。

## 检测 cadence

- **single**：一个检测器，每 `detector.interval_frames` 帧一次。
- **split**：`tracking_detector` 每 `tracking_interval_frames` 帧；`fatigue_detector` 每
  `fatigue_interval_frames` 帧。两个 backend 指向同一对象时只推理一次并复用。
- tracker 每帧运行，使用 `tracker.hold_last_s` 内的最后观测。
- 只有疲劳检测器实际运行的帧才写入 PERCLOS 样本；跳帧不会被当成“睁眼”。

Pi 默认：YuNet 每帧 + MediaPipe 每 2 帧。Desktop 默认：单个 MediaPipe 每帧。

## 模型

模型不提交仓库。`avfm models download` 下载到 `models/`（或 `--model-dir` / `AVFM_MODEL_DIR`）
并校验 SHA-256。

| 模型 | URL | SHA-256 | 大小 | 许可证 |
|---|---|---|---:|---|
| YuNet `face_detection_yunet_2026may.onnx` | `https://media.githubusercontent.com/media/opencv/opencv_zoo/26cc381e4d2594bb9f47a26eb8fd96c94a13660d/models/face_detection_yunet/face_detection_yunet_2026may.onnx` | `ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0` | 229,738 B | MIT (Shiqi Yu) |
| MediaPipe Face Landmarker `face_landmarker.task` | `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task` | `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff` | 3,758,596 B | Apache-2.0 |

不用 Haar 的原因：OpenCV 5 把 Haar/HOG 移入 contrib，pip wheel 不再带
`cv2.data/haarcascades`（opencv-python issue #1244）。不用 `mp.solutions` 的原因：
MediaPipe 0.10.31+ 移除了 legacy Solutions API。

## 会话格式

`var/runs/<timestamp>/run.json` 包含解析后的配置、source/detector/actuator、版本、起止时间和
`RunReport` 性能指标。

`session.jsonl` 每行有 `type`：

- `observation`：时间戳、画面尺寸、bbox、score、detector、metrics；
- `command`：pan、tilt、速率、applied、reason；
- `fatigue`：状态、EAR、PERCLOS/覆盖率/ready、姿态、眨眼率；
- `event`：事件名、时间戳、payload。

默认不写像素；`--record-video` 单独写带标注 MP4。

## 错误处理

- `ConfigError`：TOML 值/范围非法。
- `DependencyMissingError`：可选包缺失，带安装/apt 提示。
- `ModelNotFoundError` / `ModelVerificationError`：模型缺失或校验失败，带下载命令。
- `CameraError`：相机打不开或持续无帧。
- `ActuatorError`：请求的物理执行器初始化失败。
- `auto` 的检测器/执行器降级会写日志、写 `run.json`、在 `doctor` 可见，不静默。
