# 性能

## 父项目先验证据

父项目 `BJTU_Desktop-Learing-Assistant` 在 Raspberry Pi 5 上实测：

- 最终配置：640×480 @ 15 fps；
- `face_detection_interval = 1`（Haar 每帧）；
- `distraction_interval_frames = 2`（MediaPipe 每 2 帧，7.5 Hz）；
- 调参后跟踪和走神检测的及时性、准确性满足要求；
- 初期 MediaPipe 卡顿，通过跳帧/降采样解决。

更早文档还记录过低负载档：Haar 每 3 帧（5 Hz）+ MediaPipe 每 5 帧。最终 commit 在实测后改成更密的 cadence。

这是**父实现**的证据，不是本仓库新代码的验证。新代码用 YuNet 替代 Haar、用 MediaPipe Tasks
替代 legacy Solutions API，所以必须在硬件上重新基准。

## 新性能档

| Profile | 分辨率/FPS | 跟踪 | 疲劳 | 目的 |
|---|---|---|---|---|
| `desktop` | 640×480 @ 15 | 单检测器每帧 | 同 | Windows 笔记本 |
| `rpi` | 640×480 @ 15 | YuNet 每帧 | MediaPipe 每 2 帧 | Pi 默认 |
| `rpi_low_power` | 480×360 @ 10 | YuNet 每 2 帧 | MediaPipe 每 3 帧 | 发热/卡顿 |
| `rpi_passive` | 640×480 @ 15 | YuNet 每帧 | MediaPipe 每 2 帧 | Pi 摄像头、无舵机 |
| `rpi_tracking_only` | 640×480 @ 15 | YuNet 每帧 | 关闭 | 不装 MediaPipe |

cadence 可配置：

```toml
[detector]
mode = "split"
tracking_backend = "yunet"
fatigue_backend = "mediapipe"
tracking_interval_frames = 1
fatigue_interval_frames = 2
```

## 指标

`run.json` 记录：

- `loop_fps`、`tracking_hz`、`fatigue_hz`；
- `avg_loop_ms`、`p95_loop_ms`；
- `avg_tracking_detect_ms`、`avg_fatigue_detect_ms`；
- `dropped_frames`、`errors`。

第一帧包含模型初始化，不具代表性；HIL 数字用 `scripts/rpi_bench.py`（会丢弃 warm-up）。

## Windows 开发笔记本实测（v0.1.1）

| 项目 | 结果 |
|---|---|
| Python / OpenCV / MediaPipe | 3.11.17 / 5.0.0 / 1.1.1 |
| 核心测试 | 132 passed；81% 覆盖率 |
| YuNet on `tests/data/astronaut.jpg` | 1 张脸，score 0.932 |
| MediaPipe 同图 | 1 张脸，478 landmarks，EAR 0.308，yaw 34.2°，pitch 5.6°，roll 11.7° |
| 摄像头 passive 5 s | 58 帧，约 11.5 fps，平均 loop 约 15.9 ms |
| 带标注视频 3 s | 30 帧，写出 `annotated.mp4` |
| `avfm selftest` | step 稳定 0.53 s，超调 0.022；sine RMSE 0.088；lost 扫描/重捕获有报告 |

自动运行期间不保证摄像头前有人脸；检测精度由公有领域测试图覆盖。真人脸摄像头跟踪是手动 smoke 项。

## Pi 5 HIL 流程

有硬件时：

```bash
conda run -n avfm python scripts/rpi_bench.py --profile rpi --duration 30 --json var/bench_rpi.json
conda run -n avfm python scripts/rpi_bench.py --profile rpi_low_power --duration 30
conda run -n avfm python scripts/rpi_bench.py --profile tracking_only --duration 30
```

目标（起点，不是保证）：

- 控制环 ≥ 10 fps；
- 跟踪检测 ≥ 10 Hz；
- 疲劳采样 ≥ 5 Hz；
- 无明显卡顿、跟踪稳定、不热降频。

如果 `rpi` 不达标，用 `rpi_low_power` 或 `rpi_tracking_only`；把实测值写进本文和 README 验证矩阵。
