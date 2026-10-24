# AGENTS.md — every-picture-tells-a-story

> 供 AI 助手在本仓库工作前阅读。本仓库是"电视电影海报墙"的独立开源版：
> 数据管线（清单 → 豆瓣抓海报 → 颜色分析）+ Chrome 插件 + cleanyourtv 启动器的
> 海报墙渲染补丁。项目结构约定仿 cleanyourtv，但完全独立、只依赖 adb。

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
