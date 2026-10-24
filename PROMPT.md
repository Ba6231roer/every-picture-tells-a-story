# 首次会话提示词（PROMPT）

**用法**：把本仓库克隆/下载到电脑后，打开你的编程助手（Claude Code、Codex、
ZCode、Gemini CLI……），把下面整段提示词粘贴进去发送。提示词里假设你已读过
[README](README.md)；电视端的准备步骤写在提示词开头，照做即可。

**不使用 AI 助手？** 手动路径同样可行：`tools/` 下每个脚本都能独立运行，
按 [README 快速开始](README.md) 的顺序逐条执行即可，遇到问题看 docs/。

---

## 电视端准备（开始前照做一次）

1. 电视设置 → 设备偏好设置 → 关于 → 对"构建版本"连按 OK 7 次 → 提示已进入开发者模式；
2. 返回 → 开发者选项 → 打开「USB 调试」，有「网络 ADB 调试」的也打开；
3. 电视保持开机、与电脑同一 Wi-Fi。

部分电视在 USB 调试开启时会切断 USB 口供电——插在电视 USB 口上的音箱/硬盘会失电，
属于正常现象，结束后关掉调试即可恢复。

---

## 提示词（整段复制粘贴）

```
我想把我看过的电影海报，做成我电视上的一面自动翻转的电影海报墙。项目已经在我
的电脑上了（就是你正在读的这个仓库），按它的 README 和 AGENTS.md 来做，在真实
设备上一步步操作，每一步用截图从电视上验证。遇到需要我做决定的先问我。

我的电视： <IP:PORT 或型号>。开发者选项和 ADB 调试已打开。

0) 先读 README.md、AGENTS.md 和 docs/，然后 python tools/env_check.py 检查我的
   电脑环境。缺什么装什么：Python 用 winget 或华为镜像（mirrors.huaweicloud.com/python）；
   pip 加 -i https://mirrors.aliyun.com/pypi/simple/；adb 缺失先试
   winget install Google.PlatformTools，不行用 googledownloads.cn 的 platform-tools 包。

1) python tools/tv_check.py 检测电视适配度，把结果讲给我听。

2) python tools/backup_tv.py —— 先备份（默认桌面/应用列表/设置/截图），
   给我看恢复命令，确认我理解了"怎么还原"再继续。

3) 确认 cleanyourtv 启动器：已装则检查版本是否含海报墙支持（本仓库 patches/ 的
   日期）；未装则按 docs/TV-COMPAT.md 的三个方案和我确认装哪种。

4) 影单：问我用哪种——
   a. 豆瓣「我的影单」（我会登录豆瓣，插件里选"豆瓣我的影单"模式）；
   b. 我自己的清单文件（让我照 docs/MOVIE-LIST.md 写好，跑 parse_list.py）；
   c. 不抓，直接用仓库自带的默认海报包。
   引导我在 Chrome 里以开发者模式加载 extension/ 插件并登录豆瓣，跟我要抓哪批。

5) 抓海报走插件（保持人速，默认 6 秒/部），完成后：
   python tools/merge_extension_results.py
   python tools/build_manifest.py
   python tools/push_theme.py --theme themes/example-kd55x9100h
   每步之间截图从电视上验证效果。

6) 收尾：提醒我电视上的网络 ADB 端口是明文，确认要不要关掉；演示动图可以用
   scrcpy 录（AGENTS.md 里有参数，screenrecord 只有 5fps 别用）。

全程：改电视之前先备份；任何不确定先问我；所有电视端写入都要可逆。
```

## 常见坑（AI 会自己处理，列在这里供人工排查）

- 豆瓣对未登录脚本软封锁：HTTP 200 但内容为空 → 必须用浏览器登录态（见
  [docs/PRIVACY.md](docs/PRIVACY.md)）；
- 部分固件（TCL 等）把 shell 锁在 Android/data 之外 → 推送工具自动走
  `/data/local/tmp` 暂存，无需处理；
- 中文海报文件名：暂存路径只用 ASCII 序号，电视端 `cp` 成中文名（单引号包裹）；
- Windows 控制台中文乱码：脚本已做 UTF-8 输出重配置；
- screenrecord 录屏只有 ~5fps：录演示动图用 scrcpy。
