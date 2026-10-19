# 硬件参考

这是从父项目继承的参考结构；其他云台只要实现 `Servo` 协议即可（见 [porting.md](porting.md)）。

## 物料清单

| 部件 | 作用 | 连接 |
|---|---|---|
| Raspberry Pi 5 | 主机 | — |
| OV5647 CSI 摄像头 | 图像 | MIPI CSI-2，15-pin FPC |
| PCA9685 | 16 路 PWM 驱动 | I2C 0x40，SDA GPIO2（pin 3），SCL GPIO3（pin 5） |
| SG90 pan 舵机 | 水平 | PCA9685 CH2 |
| SG90 tilt 舵机 | 俯仰 | PCA9685 CH3 |
| 外部 5V ≥2A 电源 | 舵机供电 | 与 Pi 共地 |
| 散热 | Pi 5 散热 | 建议散热片/风扇 |

## 接线与供电

- PCA9685 VCC 接**外部 5V**，不要接 Pi 5V。
- PCA9685、舵机电源和 Pi 必须共地。
- 舵机信号线接 CH2（pan）和 CH3（tilt）。
- 运行前检查 I2C：`sudo i2cdetect -y 1` 应看到 `0x40`。
- CSI 线要避开运动中的云台，并做应力释放。

## 参考限位

| 轴 | 最小 | 最大 | 默认/park |
|---|---:|---:|---:|
| Pan | 40° | 180° | 90° |
| Tilt | 0° | 140° | 80° |

父项目用这些限位避免拉扯摄像头线。你的结构可能不同，改 profile 的 `[gimbal]` 和 `[tracker]`。

## 父项目硬件参考

父项目（`BJTU_Desktop-Learing-Assistant`）在 Pi 5 上真实跑过，它的硬件配置就是本脚手架的参考：

| 项目 | 父项目实测值 |
|---|---|
| 摄像头 | OV5647 + Picamera2，RGB888，640×480 @ 15 fps |
| 摄像头安装 | 物理倒装，软件做垂直翻转 |
| PCA9685 | I2C 0x40，50 Hz，脉冲 500–2500 µs，actuation range 180° |
| Pan | CH2，40–180°，默认 90° |
| Tilt | CH3，0–140°，默认 80° |
| 舵机驱动 | Adafruit ServoKit，16 通道统一配置一次 |

新脚手架保持这些电气和机械限位。差别是：父项目 `set_angle()` 里有运动时间 sleep，新代码改成
非阻塞；同时增加了启动失败清理和硬件降级。新代码仍然只做了契约测试，必须完成 HIL 后才能说
树莓派后端已验证。

不要根据舵机的标称角度猜脉冲范围；以实际舵机手册为准，并保持外部 5V 供电和共地方式与父项目一致。

## 摄像头安装

参考摄像头倒装，所以 `configs/rpi.toml`：

```toml
[camera]
source = "picamera"
flip = "vertical"
```

正常安装用 `flip = "none"`。如果 pan/tilt 方向反了，改 `tracker.invert_pan` /
`tracker.invert_tilt`，不要改代码里的符号。

## 树莓派软件

```bash
sudo apt update
sudo apt install -y git i2c-tools libgl1 libglib2.0-0 libportaudio2
sudo raspi-config   # 启用 I2C；当前 Pi OS 默认启用摄像头
libcamera-hello --list-cameras
sudo i2cdetect -y 1
```

然后：

```bash
conda create -n avfm python=3.11 -c conda-forge -y
conda run -n avfm python -m pip install -e ".[dev,mediapipe,rpi]"
conda run -n avfm avfm models download --all
conda run -n avfm avfm doctor --probe-camera --probe-actuator
```

`picamera2` 通常用 `sudo apt install -y python3-picamera2` 安装。若使用独立 Python 环境，
要确保 `picamera2` 绑定和 `libcamera` 对该环境可见。

## 只有摄像头、没有舵机（passive）

用 `--servo none` 和 `configs/rpi_passive.toml`。相机固定，画面内跟踪、期望 pan/tilt 记录、
疲劳检测都正常；不做物理扫描。

## 安全

- 舵机用外部电源，电流要足够；欠压可能导致 Pi 复位。
- 先单轴小角度测试，再启用 PID。
- 手远离云台；准备好急停/拔舵机电源。
- 不要把本项目当作安全认证设备。
