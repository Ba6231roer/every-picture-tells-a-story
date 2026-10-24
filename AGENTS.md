# AGENTS.md — every-picture-tells-a-story

> 供 AI 助手在本仓库工作前阅读。本仓库是"电视电影海报墙"的独立开源版：
> 数据管线（清单 → 豆瓣抓海报 → 颜色分析）+ Chrome 插件 + cleanyourtv 启动器的
> 海报墙渲染补丁。项目结构约定仿 cleanyourtv，但完全独立、只依赖 adb。

## 首次会话固定流程（用户第一句话通常是"帮我准备环境并装到电视"）

用户很可能**没有 Python、没有 adb、不懂 adb**。不要假设任何环境，按序执行：

1. 通读 `README.md`、本文、[PROMPT.md](PROMPT.md)（即贴即用的首会话提示词，用户的
   期待以它为准）与 `docs/`；
2. **Python 缺失**：`winget install Python.Python.3.12`，或华为镜像
   `mirrors.huaweicloud.com/python` 下载安装器；pip 一律加
   `-i https://mirrors.aliyun.com/pypi/simple/`（中国网络直连 PyPI 很慢）；
3. **adb 缺失**：`winget install Google.PlatformTools`，或 googledownloads.cn 的
   platform-tools 包（Google 中国下载 CDN，境内可达）；装完 `setx ADB <路径>`；
4. `python tools/env_check.py` → 逐项补齐 → `python tools/tv_check.py`；
5. **任何改电视的操作之前**：`python tools/backup_tv.py`，并把 REPORT.md 里的恢复
   命令念给用户听——大部分人最怕搞坏电视，这一步是信任基石；
6. 之后按 PROMPT.md 的步骤走（launcher 三方案 → 影单 → 插件抓海报 → 推送 → 验证）。

用户没提的偏好（dock 风格、色调、抓哪批）一律先问再做。

## 结构

| 路径 | 内容 |
|---|---|
| `extension/` | Chrome 插件（MV3，无构建步骤）：清单文件 / 豆瓣我的影单 两种素材来源 |
| `tools/` | 全部 Python 工具；`common.py` 是共享库（路径/adb/电视操作），**路径一律相对项目根，禁止硬编码绝对路径** |
| `posters/` | 默认海报包，命名 `<电影名>_<年份>.jpg`（`pw_names.py` 的 safe_file，Windows 非法字符映射全角） |
| `data/movies.json` | **唯一事实源**：片名/年份/评分/海报文件。所有脚本以它为准 |
| `data/manifest.json` | 颜色分析结果（色调池 + 每张海报 avg/dom），由 `build_manifest.py` 生成 |
| `themes/*/` | 主题：config.json（电视端参数）；posterwall/ 由 `build_manifest.py` 自动同步 |
| `preview/` | HTML 预览（fetch 相对路径 `../data`、`../posters`，从项目根起 http 服务） |
| `patches/` | 给 cleanyourtv 启动器的海报墙渲染补丁（由其 git 工作区生成） |

## 关键规则

1. **幂等**：所有脚本可反复重跑；movies.json 增量写；海报名确定性；
2. **匹配三级**（插件 content.js 与本地脚本同规则）：归一化（含"之/的"折叠）→
   评分不中信任豆瓣排序取首条带图（结果标 loose）→ 候选无图才失败；
   条目号直抓（`subject` 字段）优先于一切，用于 suggest 查不到的冷门片；
3. **本机浏览器渲染怪癖**："rgba(0,0,0,0) → rgb(0,0,0)" 的 CSS 径向渐变不渲染
   （红色正常）——暗角必须用 Canvas 逐像素贴图，不要改回 CSS 渐变；
4. **电视端模糊层刷新节奏**：翻转期间 160ms 连续快照（内容跟上翻转）、静止期只在
   零星换片后同步——周期性重拍会产生"每轮重新渲染"的观感，用户已明确反对；
5. **豆瓣限流**：suggest 对本机直连软封锁（HTTP 200 恒空）——稳定抓取一律走
   Chrome 插件（登录态 + 人速 ≥6s/请求）；本地脚本仅作解析与合并；
6. **推电视安全**：所有写操作走 `/data/local/tmp` 暂存 + `cp`（中文文件名用单引号
   包裹、暂存名只用 ASCII 序号）；push 前必须先跑过 `backup_tv.py` 的说明在 README；
7. **gradle**：构建 cleanyourtv launcher 前把 wrapper 的 distributionUrl 换成
   腾讯镜像，构建完还原（见 cleanyourtv 仓库 AGENTS.md）。
