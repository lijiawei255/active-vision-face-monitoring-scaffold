# 合规与许可

## 项目许可证

MIT — 见 [`LICENSE`](../../LICENSE)。Copyright (c) 2026 Jiawei Li。

与父项目一致，没有改许可证。MIT 与所有直接依赖和模型兼容。

## 第三方组件

| 组件 | 许可证 | 分发方式 |
|---|---|---|
| OpenCV / `opencv-contrib-python` | Apache-2.0 | pip 依赖 |
| NumPy | BSD-3-Clause | pip 依赖 |
| MediaPipe | Apache-2.0 | 可选 pip 依赖 |
| MediaPipe Face Landmarker 模型 | Apache-2.0 | `avfm models download` 下载，不提交 |
| YuNet `face_detection_yunet_2026may.onnx` | MIT（Copyright (c) 2020 Shiqi Yu） | 下载，不提交 |
| Picamera2 | BSD-2-Clause | 可选 Pi 依赖 |
| Adafruit CircuitPython ServoKit / Blinka | MIT | 可选 Pi 依赖 |
| pytest / ruff / pre-commit / build | MIT | 开发依赖 |
| twine | Apache-2.0 | 开发依赖 |
| NASA 宇航员测试图 | 公有领域（NASA Great Images，无已知版权限制） | 提交为 `tests/data/astronaut.jpg`，带署名 |

传递依赖的许可证保留在安装环境中。链接见 [`THIRD_PARTY_LICENSES.md`](../../THIRD_PARTY_LICENSES.md)。

## 没有无许可证代码

prior-art 表列出没有许可证的项目，仅引用思路；没有复制代码。MIT 项目仅引用；本实现是重写。

## 隐私

- 运行在本地处理；不上传帧。
- 不做人脸识别、身份库或 embedding。
- 默认不录像；`--record-video` 显式开启；JSONL 只存框/指标/事件，不存像素。
- 用于工作场所、车辆或教室监测时，部署者需遵守当地法律并取得知情同意
  （GDPR、澳大利亚 Privacy Act、工作场所监控法规等）。
- 不要把个人人脸图或录像提交到仓库。仓库中唯一的人脸图是公有领域 NASA 测试图。

## 安全

- 疲劳指标是启发式的；不是医疗器械，也不是经过认证的驾驶员监控系统。
- 不要用于安全关键决策。
- 舵机供电、机械限位和急停由搭建者负责。

## 商标

Raspberry Pi、MediaPipe、OpenCV 是各自所有者的商标。本项目仅做事实性引用，不隶属于它们，
也不代表官方背书。

## Anaconda 与 CI

- `environment.yml` 只用 `conda-forge`，不用 Anaconda `defaults`。
- GitHub Actions 用 `pip` 和标准 Python 环境，不用 Anaconda。
- CI 权限 `contents: read`，无 secrets，无 `pull_request_target`。

## 出口管制

不包含受控加密或出口限制组件。
