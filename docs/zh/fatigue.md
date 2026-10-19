# 疲劳指标

> 这些是启发式指标，不是医学诊断，也不是经过认证的驾驶员监控系统。PERCLOS 是研究指标，
> 不同研究的实现和阈值并不统一。

## EAR（Eye Aspect Ratio）

每只眼睛用 6 个 MediaPipe 关键点：

```text
EAR = (|p1-p5| + |p2-p4|) / (2 * |p0-p3|)
```

用像素坐标而不是归一化坐标，避免 640×480 等非方形画面破坏比例。单眼无效时用另一只；
双眼都无效则标记该帧对疲劳无效。

- 默认阈值：0.2。
- `avfm calibrate ear` 采集睁眼样本，设置
  `threshold = clip(median * ratio, floor, ceiling)`。
- 典型值受个人、眼镜、光照、相机角度影响；这些变化后要重新校准。

## 眨眼、微睡眠与 PERCLOS

- **眨眼**：闭眼时长在 `blink_min_s`（0.05 s）到 `blink_max_s`（0.4 s）之间后睁开。
- **微睡眠**：连续闭眼 ≥ `microsleep_s`（1.5 s）→ `DROWSY`。
- **PERCLOS**：滚动 `perclos_window_s`（60 s）内，EAR 低于阈值的有效样本比例。要求：
  - 至少 `perclos_warmup_s`（30 s）历史；
  - 有效样本覆盖率 ≥ `perclos_min_coverage`（0.8）；
  - 最近样本不超过 `perclos_max_gap_s`（0.5 s）。
- 0.4–1.5 s 的闭眼既不算眨眼，也不立即判睡，只贡献 PERCLOS。

无效样本（无脸、无关键点、姿态门控）会写成 invalid，避免“没数据 = 清醒”。
`perclos_ready=False` 表示“数据不足”，不是“清醒”。

## 头部姿态与姿态门控

用 6 个 3D 模型点（鼻尖、下巴、内眼角、嘴角）匹配 6 个 MediaPipe 关键点，
`cv2.solvePnP`（优先 SQPNP，回退 iterative）。平均重投影误差低于 `max_reproj_error_px`
才算有效姿态。

- 转头：`|yaw| > distraction_yaw_deg`（20°）或 `|pitch| > distraction_pitch_deg`（15°）
  持续 `distraction_confirm_s`（2 s）→ `DISTRACTED`。
- 姿态门控 EAR：`|yaw| > ear_max_yaw_deg`（25°）或 `|pitch| > ear_max_pitch_deg`（20°）时，
  该帧 EAR/PERCLOS 样本记为 invalid，避免转头被误判为闭眼。

相机内参由 `camera.hfov_deg`（默认 60°）和方形像素假设近似。需要精确姿态时做相机标定并
提供 `fx/fy/cx/cy`。上面的阈值故意做得比较宽容。

## 状态机

优先级：`DROWSY` > `DISTRACTED` > `ALERT`；人脸缺失超过 `face_lost_s` → `NO_FACE`；
MediaPipe/疲劳不可用或关闭 → `UNAVAILABLE`。

- 进入/退出使用 `recovery_s` 迟滞。
- 事件有 `event_cooldown_s`，避免刷屏。
- 事件：`DROWSY_STARTED/ENDED`、`DISTRACTED_STARTED/ENDED`、`BLINK`。

## PERCLOS 参考

- Wierwille et al. (1994)：PERCLOS 定义为眼睛至少 80% 闭合的时间比例。
- FHWA/NHTSA Tech Brief：“PERCLOS: A Valid Psychophysiological Measure of Alertness”。
- Abe et al., “PERCLOS-based technologies for detecting drowsiness: current evidence and future
  directions”, SLEEP Advances (2023)：讨论定义和阈值的差异。

本项目用 EAR 代理眼睑闭合，不是 80% 瞳孔遮挡测量；这是面向 webcam/Pi 脚手架的工程折中。
