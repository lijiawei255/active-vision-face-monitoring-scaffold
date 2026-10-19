# 参考项目与定位

快照：GitHub，2026-10-19。星标和许可证会变化；复用前请自行核实。

| 项目 | 星标 | 许可证 | 覆盖什么 | 与本脚手架的差距 |
|---|---:|---|---|---|
| [TianxingWu/face-tracking-pan-tilt-camera](https://github.com/TianxingWu/face-tracking-pan-tilt-camera) | 245 | MIT | PC OpenCV + STM32，2-DOF 人脸跟踪，PD，图像坐标误差 | 无疲劳、无自动化测试、绑定 STM32 |
| [e-candeloro/Driver-State-Detection](https://github.com/e-candeloro/Driver-State-Detection) | 157 | MIT | Webcam DMS、MediaPipe Tasks、EAR/gaze/head pose/PERCLOS、测试 | 无云台/主动视觉；完整应用而非脚手架 |
| [akshaybahadur21/Drowsiness_Detection](https://github.com/akshaybahadur21/Drowsiness_Detection) | 548 | MIT | 经典 dlib EAR demo | 无云台、无测试 |
| [pimoroni/PanTiltFacetracker](https://github.com/pimoroni/PanTiltFacetracker) | 50 | **无** | Pi PanTilt HAT 人脸跟踪 | 无疲劳/测试；不可复制代码 |
| [pageauc/face-track-demo](https://github.com/pageauc/face-track-demo) | 45 | **无** | Pi 人脸/运动跟踪、扫描 | 无疲劳/测试；不可复制代码 |
| [Tandon-A/Drowsiness-Detection-Mediapipe](https://github.com/Tandon-A/Drowsiness-Detection-Mediapipe) | 30 | MIT | MediaPipe + LSTM、个体校准 | 无云台 |
| [sahnimanas/Fatigue-Detection](https://github.com/sahnimanas/Fatigue-Detection) | 58 | **无** | PERCLOS 疲劳 | 无云台；不可复制代码 |
| [Quackieduckie/tracking-screen](https://github.com/Quackieduckie/tracking-screen) | 1 | **无** | MediaPipe 云台 + 扫描 | 无疲劳/测试；不可复制代码 |
| [astrix884/Anti-Sleep-Robot](https://github.com/astrix884/Anti-Sleep-Robot) | 0 | **无** | 人脸跟踪 + 疲劳 + ESP32 炮塔 | 玩具，无测试/许可证 |
| [luvmangla05/LumiTrack](https://github.com/luvmangla05/LumiTrack) | 0 | **无** | 不同领域的 SIL PID 云台平台 | 无许可证；仅参考 |
| PyImageSearch pan-tilt 教程 | — | 不明确 | PID + pan/tilt 教学 | 代码许可不明确；不复制 |

## 生态缺口

- 只有疲劳检测的项目：检测 demo/应用不错，但没有主动相机控制。
- 只有跟踪的项目：大量单文件 demo、硬件写死、无测试，有时无许可证。
- 两者结合：玩具或无许可证原型。
- 通用 Python/CV 脚手架：没有领域相关的控制/疲劳契约。

## 本项目的定位

一个**有维护、MIT、有测试的工程脚手架**，位于以下交集：

1. 2-DOF PID 云台人脸跟踪；
2. EAR/PERCLOS/头部姿态疲劳指标；
3. 硬件抽象（webcam/Pi 相机，null/mock/PCA9685）；
4. passive/无舵机运行；
5. SIL、回放、契约测试和 CI；
6. Raspberry Pi 5 参考后端与性能档。

价值在集成、可测试性和文档，不是新检测算法。

## 复用政策

- 没有从上面无许可证项目复制代码；仅引用思路和对比。
- MIT 项目仅引用；本实现是重写。
- 父项目是 MIT，来源见 [provenance.md](provenance.md)。
