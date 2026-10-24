# 电视适配度与环境要求

## 开发机（跑工具用）

| 项 | 必需性 | 说明 |
|---|---|---|
| Python ≥ 3.9 + Pillow | 必需 | 清单解析、颜色分析、合并 |
| adb（platform-tools） | 必需 | 一切电视交互 |
| Chrome + 本仓库插件 | 抓海报必需 | 见 extension/ 与 docs/PRIVACY.md |
| ffmpeg | 可选 | 录屏转 GIF/WebP |
| scrcpy | 可选 | 流畅录屏（~14fps） |
| JDK 17 + Android SDK + gradle | 仅自建 launcher 时 | 见 patches/ 说明 |

`python tools/env_check.py` 会逐项检查并给出安装提示。

## 电视

| 项 | 要求 | 不满足时 |
|---|---|---|
| Android ≥ 8.0（API 26） | 必需（launcher minSdk） | 无法安装，检测脚本会直接报告 |
| adb 调试已开启并授权 | 必需 | 电视设置 → 关于 → 连按版本号开启开发者选项 |
| 剩余空间 ≥ 100MB | 推荐 | 海报包约 15MB |
| Android/data 可写 | 可选 | 锁住的固件（部分 TCL）自动走暂存通道 |
| 实时边缘模糊 | Android 12+ 才有系统 API | Android 10-11 用定期快照近似（本项目方案） |

## 已实测设备

| 设备 | 系统 | 结果 |
|---|---|---|
| Sony KD-55X9100H（MTK，国行） | Android 10 | ✅ 全功能（本文档的基准设备） |
| 其他 | — | 欢迎提 issue 反馈 |

## 已知的固件差异

- **Android/data 锁**：部分 TCL/LG 固件禁止 shell 访问应用的 external files 目录。
  推送工具自动走 `/data/local/tmp` 暂存 + `cp`（或 content provider）方案，
  `tv_check.py` 会提前检测；
- **编码器性能**：`screenrecord` 在多数电视上只有 ~5fps（录出来的视频卡顿），
  录演示动图请用 scrcpy（PC 端编码，~14fps）；
- **启动器被厂商覆盖**：部分电视重启后会把厂商桌面设回默认。cleanyourtv 仓库有
  完整的应对方案（freeze 厂商桌面），属其职责范围，本项目不重复。
