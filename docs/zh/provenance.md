# 来源说明

## 父项目

本仓库从以下项目的视觉子系统抽取并重写：

- [BJTU_Desktop-Learing-Assistant](https://github.com/lijiawei255/BJTU_Desktop-Learing-Assistant)
- MIT License，Copyright (c) 2026 Jiawei Li
- 视觉相关源码 commit：[`bc270b0`](https://github.com/lijiawei255/BJTU_Desktop-Learing-Assistant/commit/bc270b0)
  （“摄像头帧翻转+跟踪停止+每帧检测”）
- 抽取时父项目最新 commit：`952cccf`

## 抽取的概念

来自 `src/devices/camera.py`、`src/devices/servo_controller.py`、`src/devices/servo_mock.py`、
`src/processes/vision_process.py`、`src/config.py` 及父项目文档：

- PID pan/tilt 人脸跟踪、死区、自动扫描；
- Face Mesh EAR/头部姿态走神检测；
- PCA9685 + SG90 限位、摄像头翻转、mock 舵机/摄像头；
- Pi 5 性能档：640×480@15fps，跟踪每帧，MediaPipe 每 2 帧。

## 行为变化

| 父项目行为 | 本脚手架 |
|---|---|
| `mp.solutions.face_mesh` | MediaPipe Tasks `FaceLandmarker` + 下载模型 |
| 从 `cv2.data.haarcascades` 加载 Haar | YuNet `cv2.FaceDetectorYN`（OpenCV 5 核心 pip wheel 无 Haar 数据） |
| 像素误差 × `0.05` 魔法增益 | 速度式 PID，单位 °/s，含 dt、限幅、抗饱和、死区 |
| `set_angle()` 最多 sleep 2 秒 | 非阻塞命令；速率限制在控制器 |
| 全局 `config` 单例 | typed dataclass + TOML profile + 校验 |
| 人脸框无限期保持 | 观测 TTL（`hold_last_s`） |
| 帧数阈值 | 基于时间的眨眼/微睡眠/PERCLOS 阈值 |
| 固定 EAR 阈值 | 可选按人校准 |
| 无 PERCLOS | 带覆盖率/新鲜度的滚动 PERCLOS |
| 无 passive 模式 | 一等 passive/无舵机模式 |
| 无 SIL/回放/CI | 虚拟 plant、JSONL 回放、pytest、GitHub Actions |

## 没有复制什么

- 没有复制 [prior-art.md](prior-art.md) 中无许可证项目的代码。
- 没有复制父项目的 API key、`.env`、用户人脸图、demo 视频或个人数据。
- 父项目的 LLM/音频/手机盒/TOF/LED/IR/按钮模块不在范围内。

## 许可证

MIT。父项目是 MIT，抽取/重写兼容。再分发时保留原版权声明和本来源说明。
