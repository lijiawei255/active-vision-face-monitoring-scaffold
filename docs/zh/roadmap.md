# 路线图

## v0.1.x

- Raspberry Pi HIL：`scripts/rpi_smoke.py`、`scripts/rpi_bench.py`，公开实测数字。
- 修复真实 Picamera2/PCA9685 硬件上发现的问题。
- 在 `docs/en`/`docs/zh` 增加 HIL 结果报告。

## v0.2

- 可选串口舵机后端（ESP32/STM32），文档化行协议和示例固件。
- 打哈欠（MAR）与 gaze/iris 指标。
- 更好的多脸选择和可选按 ID 跟踪。
- 相机标定 helper（`fx/fy/cx/cy`）。

## v0.3+

- ONNX 检测器替代与性能对比。
- MkDocs/GitHub Pages 文档站。
- PyPI 发布（`avfm` 名称当前可用）。
- 可选 Docker/无头部署说明。
- CodeQL/OpenSSF Scorecard 与发布自动化。

## 明确的非目标

- 人脸识别/身份。
- 医疗或安全认证。
- 云上传或托管仪表盘。
- 开箱即用的终端应用。
