# 测试

## 测试金字塔

| 层级 | 内容 | 需要硬件？ | CI？ |
|---|---|---|---|
| 单元 | PID、Gimbal、Tracker、EAR、HeadPose、PERCLOS、状态机、配置、模型、校准 | 否 | 是 |
| 契约 | 伪 MediaPipe、伪 Picamera2、伪 ServoKit、检测 cadence | 否 | 是 |
| 真实检测器 | 公有领域图上的 YuNet/MediaPipe | 否 | 是（下载模型） |
| SIL | 虚拟云台 plant + 人脸轨迹 + PID/扫描 | 否 | 是 |
| 集成 | pipeline single/split/passive/mock、CLI、overlay、JSONL、回放 | 否 | 是 |
| Webcam | 本机摄像头采集与 passive 循环 | 摄像头 | 手动/显式 |
| HIL | Picamera2 + PCA9685 + 舵机 + benchmark | Pi | 手动/显式 |

## 命令

```bash
# 核心（无摄像头、无 Pi 硬件、可不装 MediaPipe）
pytest -m "not webcam and not hardware and not mediapipe" \
  --cov=avfm --cov-fail-under=80

# 真实模型（MediaPipe 需要可用的 GL/EGL 栈）
pytest -m "mediapipe or model" --run-mediapipe

# 本机摄像头
pytest -m webcam --run-webcam

# 树莓派硬件
pytest -m hardware --run-hardware
```

标记在 `pyproject.toml` 注册：`model`、`mediapipe`、`webcam`、`hardware`、`slow`。

## 静态检查

仓库自带 `py.typed`，因此 `src/` 的类型检查是承诺而不是装饰：CI 与 pre-commit 都会执行。

```bash
ruff check src tests
ruff format --check src tests
mypy          # 仅 src；配置在 pyproject.toml
```

## 依赖锁文件

CI 不再现场解析版本范围，而是从 `requirements/` 安装精确且带哈希的版本。

| 文件 | 用途 |
|---|---|
| `lock-core.txt` | 仅运行时依赖（wheel 冒烟测试） |
| `lock-dev.txt` | lint、核心测试、文档检查 |
| `lock-dev-mediapipe.txt` | MediaPipe/模型测试 |

依赖变化后重新生成三份锁文件；lint job 会在它们漂移时失败。

```bash
uv pip compile pyproject.toml --universal --python-version 3.11 \
  --generate-hashes -o requirements/lock-core.txt
uv pip compile pyproject.toml --extra dev --universal --python-version 3.11 \
  --generate-hashes -o requirements/lock-dev.txt
uv pip compile pyproject.toml --extra dev --extra mediapipe --universal \
  --python-version 3.11 --generate-hashes -o requirements/lock-dev-mediapipe.txt
```

`rpi` extra 依赖仅限 Linux 的 `picamera2`，因此在 Pi 上用 `pip install -e ".[rpi]"` 安装，
不进入通用锁文件。

## SIL 场景

`avfm simulate` 和 `scripts/rpi_bench.py` 使用一阶 pan/tilt plant 和投影人脸位置。
`avfm selftest` 的验收：

- step ±20°：稳定，最终误差 < 0.05，超调 < 0.25；
- sine ±20°/8 s：RMSE < 0.1，最大误差 < 0.2；
- lost 5 s：触发扫描；报告重捕获时间；
- cadence：tracking/fatigue 检测器按配置帧索引调用；PID 每帧运行。

## 测试图

`tests/data/astronaut.jpg` 是 scikit-image `astronaut` 样本的缩放派生图：

- NASA Great Images，公有领域，无已知版权限制；
- 人物：宇航员 Eileen Collins；
- 仅用于检测器/关键点提取验证，不用于身份识别或训练。

见 `tests/data/README.md`。

## HIL 清单（树莓派）

1. 断电；检查外部 5V、共地、线缆应力释放。
2. `libcamera-hello --list-cameras`；`sudo i2cdetect -y 1` 看到 `0x40`。
3. 运行 `avfm doctor --probe-camera --probe-actuator`。
4. 先 passive（`--servo none`），确认人脸检测/EAR/PERCLOS。
5. 单轴小角度扫舵机；确认限位和方向。
6. 再 active；准备好急停。
7. 运行 `scripts/rpi_bench.py` 的 `rpi`、`rpi_low_power`、`tracking_only`；记录结果。
8. 运行 `scripts/rpi_smoke.py`；把 `var/hil_report.json` 附到 hardware report issue。

在脚本输出存在之前，不要把 HIL 报告成已通过。
