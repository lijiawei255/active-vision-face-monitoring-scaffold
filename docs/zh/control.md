# 控制设计

## PID 形式

每个轴使用速度式 PID：

```text
误差 e = 归一化人脸偏移（正 = 偏右/偏下）
积分 I += e * dt            （限幅）
微分 D = (e - e_prev) / dt
输出 u = Kp*e + Ki*I + Kd*D （限幅到 ±output_limit，单位 °/s）
角度 += sign * u * dt       （按 ±max_step_deg 和机械限位钳位）
```

- `output_limit` 单位是 **°/s**，不是度。
- `integral_limit` 单位是 error·秒；输出饱和且误差同向时冻结积分。
- 死区内输出 0，积分按 `integral_decay` 泄漏，避免人脸重新进入时跳变。
- `max_step_deg` 是单次更新的最终安全钳位。
- `invert_pan` / `invert_tilt` 适配机械安装方向。

## 默认值与调参

仓库默认值由 SIL plant 调出：

```toml
[tracker]
deadband_x = 0.03
deadband_y = 0.03

[tracker.pan_pid]
kp = 120.0
ki = 5.0
kd = 1.2
output_limit = 240.0

[tracker.tilt_pid]
kp = 100.0
ki = 5.0
kd = 1.0
output_limit = 200.0

[gimbal]
max_step_deg = 10.0
```

这些是起点，不是通用增益。调参：

```bash
avfm simulate --scenario step --duration 12
avfm simulate --scenario sine --duration 12
```

`avfm selftest` 的验收：

- step：稳定，最终归一化误差 < 0.05，超调 < 0.25；
- sine（±20°，8 s 周期）：RMSE < 0.1，最大误差 < 0.2；
- lost：触发扫描并报告重捕获时间。

## 跟踪状态机

```text
IDLE --face--> TRACKING --lost TTL--> FACE_LOST
FACE_LOST --lost_timeout & can_actuate--> SEARCHING
SEARCHING --face--> TRACKING（PID reset，FACE_ACQUIRED）
SEARCHING --max_cycles--> IDLE（park）
```

`none` 和（默认）`mock` 的 `can_actuate` 为 False，所以 passive 模式不会做物理扫描。
观测滤波在 `hold_last_s` 内保留最后 bbox，用来桥接漏检；超时后视为丢失。

## 为什么 PID 每帧运行

检测器可能比相机慢（尤其 Pi 上的 MediaPipe）。tracker 和 PID 按相机帧率运行，使用 TTL 内的最后观测。
这样控制信号平滑，控制延迟与检测延迟解耦。

## 前馈/后续

当前是纯反馈。后续可以用 FOV 和人脸偏移计算前馈角速度，或用滤波器估计人脸深度/速度。
这些是路线图项，SIL plant 是评估它们的地方。
