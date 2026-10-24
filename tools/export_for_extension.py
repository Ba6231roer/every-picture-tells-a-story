# -*- coding: utf-8 -*-
"""把海报墙的观影清单导出成 Chrome 插件可导入的格式（data/douban_todo.json）。

默认只导出当前缺海报的片子；--all 导出全部（用于整体换豆瓣高清图）。
"""
import json
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pw_names import safe_file  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent


def main():
    all_flag = "--all" in sys.argv
    movies = json.loads((OUT / "data/movies.json").read_text(encoding="utf-8"))
    items = []
    for m in movies:
        if not all_flag and m.get("img"):
            continue
        items.append({
            "title": m["title"],
            "year": m.get("year"),
            "rating": m.get("rating"),
            "periods": m.get("periods", []),
            "file": safe_file(m["title"], m.get("year")),  # 插件直接按这个名字保存
            **({"subject": m["douban_subject"]} if m.get("douban_subject") else {}),
        })
    items.sort(key=lambda x: x["title"])
    out = {"exported": "poster-wall", "count": len(items), "items": items}
    dest = OUT / "data/douban_todo.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"douban_todo.json: {len(items)} 部 -> {dest}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
