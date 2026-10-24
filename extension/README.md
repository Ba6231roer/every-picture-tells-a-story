# 豆瓣海报抓取 Chrome 插件

MV3 插件，无构建步骤。**完全本地运行：没有服务器、没有上报、没有统计。**

## 为什么需要登录豆瓣？

海报图片在豆瓣的条目页上，而豆瓣对**未登录的脚本请求**有严格限制（返回空内容、
限流、验证码）。插件的做法是：**在你自己的浏览器里、用你自己的登录态、按你设定
的速度（默认 ≥6 秒/部）访问你本人本来就能打开的页面**——和你自己翻豆瓣没有本质
区别，只是让浏览器替你翻。

## 隐私：代码可查，数据不出本机

插件一共只有 4 个文件，全部逻辑可读：

| 文件 | 职责 |
|---|---|
| `manifest.json` | 权限声明：只有 `movie.douban.com`、`*.doubanio.com`（图片 CDN）和下载 |
| `popup.html/js` | 界面与控制 |
| `background.js` | 开豆瓣标签页、把海报存到下载目录 |
| `content.js` | 在豆瓣页面里检索条目、下载海报 |

网络请求**只有**豆瓣域名（检索 + 图片），没有任何第三方地址，没有上报。
抓到的图片存到你自己的 Chrome 下载目录，数据不出本机。

## 三种抓海报的方式

### 方式一：抓你的豆瓣影单（最省事，需登录）

1. 插件弹窗里选「豆瓣我的影单」+ 标记（看过/想看/在看）→ 开始；
2. 插件自动翻你的影单页解析全部条目，逐个抓海报。

> 仅在你本人已登录、且影单页你自己可见时有效（默认就是）。

### 方式二：清单文件（不需要豆瓣账号本身，但抓取时仍需登录态）

```bash
python tools/parse_list.py 你的观影清单.md      # 生成 data/movies.json
python tools/export_for_extension.py            # 生成 data/douban_todo.json
```

弹窗导入 `data/douban_todo.json` → 开始。每条清单项也可以手动加
`"subject": "条目数字ID"` 字段，绕过检索直接按条目号抓（冷门片兜底）。

### 方式三：手动放图（完全不碰豆瓣）

按 `data/missing_list.md` 里给出的文件名，把海报图放进 `posters/`，
跑一遍 `build_manifest.py` 自动收编。

## 抓完之后

1. 插件里点「导出结果」→ `下载目录/poster-wall/results.json`（海报 jpg 也在同目录）；
2. `python tools/merge_extension_results.py` —— 校验图片、按
   `<电影名>_<年份>.jpg` 统一命名、更新 `data/movies.json`；
3. `python tools/build_manifest.py` —— 颜色分析、色调池、manifest；
4. `python tools/push_theme.py --theme themes/example-kd55x9100h` —— 推上电视。

## 匹配规则（防抓错）

三级：①归一化评分（精确 > 前缀 > 包含 + "之/的"折叠 + 年份接近加分）；
②评分不中时**信任豆瓣自己的排序取第一条带图**（结果标 `loose: true` 供抽查）；
③候选全没图才失败。指定了 `subject` 的条目走"条目号直抓"，最可靠。

## 注意

- 抓取速度别调太快（默认 6 秒/部），对豆瓣友好一些；
- 改过插件代码后到 `chrome://extensions` 点「重新加载」；
- 电影海报版权归原作者，仅供个人欣赏，请勿商用。
