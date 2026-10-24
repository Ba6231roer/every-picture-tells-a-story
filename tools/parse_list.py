# -*- coding: utf-8 -*-
r"""把任意格式的观影清单解析成海报墙管线的数据源（data/movies.json 骨架）。

支持的行格式（可混用）：
  #### 片名：MMDD时段；YYYY上映；评论。评价良     ← cleanyourtv 式观影笔记
  \#### 片名：MMDD晚；YYYY放送；...              ← 转义井号也认
  - 片名（YYYY）★                               ← 普通列表
  片名,2024                                     ← 裸文本
  片名                                          ← 只有片名

评分从文本里的关键词提取：超优秀 > 优秀 > 良 > 中。
已存在的 data/movies.json 会被保留合并（有海报的条目不动），可放心反复跑。

用法：python tools/parse_list.py 观影清单.md [更多.md ...]
"""
import json
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

LINE_RE = re.compile(r"^\s*(?:\\+)?#{2,5}\s+(.+)$|^\s*[-*•]\s*(.+)$|^(?!#)(.+)$")


def parse_line(line):
    """一行 → (title, year, rating, star)；解析不出片名返回 None。"""
    s = line.strip()
    if not s or s.startswith(("<!--", "```")):
        return None
    # 取片名：优先"片名：日期"式切分（日期=冒号/分号后紧跟 4 位数字），否则整行
    m = re.search(r"[：:]\s*(?=\d{4})", s)
    if not m:
        m = re.search(r"[；;]\s*(?=\d{4})", s)
    title = (s[: m.start()] if m else re.split(r"[，,；;]", s)[0]).strip()
    title = title.lstrip("-*• ").lstrip("#").strip()
    if not title or len(title) > 60:
        return None
    year = None
    my = re.search(r"[（(]?\s*(19\d{2}|20\d{2})\s*年?(?:上映|放送)?", s)
    if my:
        year = int(my.group(1))
    rating = None
    for r in ("超优秀", "优秀", "良", "中"):
        if r in s:
            rating = r
            break
    return {"title": title, "year": year, "rating": rating,
            "star": "★" in s, "periods": []}


def parse_file(path):
    items = []
    for raw in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        r = parse_line(raw)
        if r:
            r["periods"] = [pathlib.Path(path).stem]
            items.append(r)
    return items


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("示例：python tools/parse_list.py 我的观影清单.md")
        return 1
    movies_path = DATA / "movies.json"
    old = {}
    if movies_path.exists():
        for m in json.loads(movies_path.read_text(encoding="utf-8")):
            old[m["title"]] = m
    fresh = []
    seen = set()
    for path in sys.argv[1:]:
        for item in parse_file(path):
            key = item["title"]
            if key in seen:
                continue
            seen.add(key)
            prev = old.get(key)
            if prev:  # 已有条目（可能已带海报）→ 原样保留
                fresh.append(prev)
                continue
            fresh.append(item)
    fresh.sort(key=lambda x: x["title"])
    DATA.mkdir(exist_ok=True)
    movies_path.write_text(json.dumps(fresh, ensure_ascii=False, indent=1), encoding="utf-8")
    n_img = sum(1 for m in fresh if m.get("img"))
    print(f"清单解析完成: {len(fresh)} 部（已有海报 {n_img}，待抓 {len(fresh) - n_img}）")
    print("下一步：chrome 插件抓海报（见 extension/README.md）→ merge → build_manifest")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
