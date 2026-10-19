# 故障排查

## 模型

**`Model file not found` / `ModelVerificationError`**

```bash
avfm models download --all
# 或
avfm models download --only yunet
avfm models download --only mediapipe
avfm models verify --all
```

只有文件损坏时才用 `--force`。模型放在别处时检查 `AVFM_MODEL_DIR` / `--model-dir`。

## MediaPipe

**`mediapipe is not installed`**

```bash
pip install -e ".[mediapipe]"
```

树莓派上 MediaPipe 是可选的。装不上就用 `configs/rpi_tracking_only.toml` 或 `--detector yunet`；
疲劳会报告为不可用。

**`module 'mediapipe' has no attribute 'solutions'`**

该 API 在 MediaPipe 0.10.31+ 已移除。本项目用 `mp.tasks`，不要用 `mp.solutions`。

## OpenCV

**`cv2.CascadeClassifier` 缺失 / `haarcascades` 为空**

OpenCV 5 把 Haar/HOG 移入 contrib，pip wheel 不再带 XML。本项目用 YuNet
（`cv2.FaceDetectorYN`），不需要 Haar。

**Linux 上 OpenCV import 失败**

安装 GUI/GL 运行库：

```bash
sudo apt install -y libgl1 libglib2.0-0
```

## 摄像头

- Windows：检查相机隐私设置，关闭占用摄像头的其他应用。
- Pi：`libcamera-hello --list-cameras`；检查 CSI 线；检查 `video` 组权限。
- 有画面但检测不到人脸：检查光照、距离（约 0.3–2 m）、模型是否下载。
- 无头 Pi 上用 `--no-show` + `--record-video`，不要用 `--show`。

## I2C / PCA9685

**`PCA9685 not found at I2C address 0x40`**

```bash
sudo i2cdetect -y 1
```

检查 SDA/SCL、共地、外部 5V 和地址跳线。总线可见前先用 `--servo none`。
`--servo auto` 探测失败会降级 passive 并给警告。

## 舵机方向/抖动

- 用 `tracker.invert_pan` / `tracker.invert_tilt` 适配安装方向。
- 舵机嗡嗡或震荡：降低 `kp` / `output_limit`。
- 在中心附近来回找：稍微增大 `tracker.deadband_x/y`。
- 外部电源要能提供两个舵机的堵转电流。

## 性能/卡顿

- 用 `configs/rpi_low_power.toml`，或降低 `runtime.fps`、分辨率、检测 cadence。
- 只做跟踪时用 `--detector yunet`。
- 跑 `scripts/rpi_bench.py`，比较 `loop_fps`、`avg_loop_ms`、`p95_loop_ms`。
- 检查散热：`vcgencmd measure_temp`。

## 测试

- `--run-webcam`、`--run-hardware`、`--run-mediapipe` 是显式开关。
- 缺模型时模型测试会 skip；先 `avfm models download --all`。
- Linux 上如果传递依赖试图开显示，设置 `MPLBACKEND=Agg`。
