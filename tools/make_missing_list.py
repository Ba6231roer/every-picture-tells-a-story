# -*- coding: utf-8 -*-
"""生成 data/missing_list.md：当前缺海报的片子 + 各自应放的文件名。

用户按文件名把海报丢进 posters/ 后，跑 build_manifest.py 会自动收编（无需改 movies.json）。
"""
import json
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pw_names import safe_file  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent


def main():
    movies = json.loads((OUT / "data/movies.json").read_text(encoding="utf-8"))
    miss = [m for m in movies if not m.get("img")]
    lines = [
        "# 缺失海报清单",
        "",
        f"共 {len(miss)} 部。想补哪部，就按下面的文件名把海报图放进 `posters/`，然后：",
        "",
        "```bash",
        "python poster-wall/tools/build_manifest.py",
        "TV_HOST=192.168.50.161 tools/theme.sh themes/kd-55x9100h",
        "```",
        "",
        "（也可以不手动放，用 Chrome 插件批量抓：chrome-extension/README.md）",
        "",
    ]
    for m in sorted(miss, key=lambda x: x["title"]):
        p = m.get("periods", [])
        lines.append(f"- **{safe_file(m['title'], m.get('year'))}**"
                     f"（{m['title']}，{m.get('year') or '年份未知'}，{','.join(p)}，{m.get('rating') or '未评分'}）")
    (OUT / "data/missing_list.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"missing_list.md: {len(miss)} 部")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
