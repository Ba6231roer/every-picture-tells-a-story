# -*- coding: utf-8 -*-
"""对 posters/ 里的海报做颜色分析，归入主色调池，产出 data/manifest.json 供 index.html 使用。

每个海报输出：
  avg  = 全图平均色（兜底渐变用）
  dom  = 主色簇颜色（剔除近黑的背景簇，取占比最大的有色簇）
  mood = dom 的 HSV 归类（黑白/红/橙/金/绿/青/蓝/紫/粉），小池按 PARENTS 并入邻近色
"""
import json
import colorsys
import pathlib
import datetime
import shutil
from collections import Counter
from PIL import Image
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from pw_names import safe_file  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent
MIN_POOL = 14
PARENTS = {"粉": "红", "青": "蓝", "金": "橙", "紫": "蓝", "绿": "青"}


def classify(rgb):
    r, g, b = [c / 255 for c in rgb]
    _, s, v = colorsys.rgb_to_hsv(r, g, b)
    hd = colorsys.rgb_to_hsv(r, g, b)[0] * 360
    if s < 0.16 or v < 0.10 or (v > 0.93 and s < 0.22):
        return "黑白"
    if 160 <= hd < 190:
        return "青"
    if 190 <= hd < 255:
        return "蓝"
    if 255 <= hd < 300:
        return "紫"
    if 300 <= hd < 345:
        return "粉"
    if hd >= 345 or hd < 15:
        return "红"
    if 15 <= hd < 45:
        return "橙"
    if 45 <= hd < 75:
        return "金"
    return "绿"


def analyze(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((120, 120))
    px = list(im.getdata())
    n = len(px)
    avg = tuple(sum(c[i] for c in px) // n for i in range(3))
    q = im.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(maxcolors=n) or [], reverse=True)

    def color_of(idx):
        return tuple(pal[idx * 3: idx * 3 + 3])

    def val(c):
        return colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)[2]

    dom = color_of(counts[0][1])
    if val(dom) < 0.10:  # 主簇近黑（海报深色底），尝试换一个够大的有色簇
        for cnt, idx in counts[1:]:
            c = color_of(idx)
            if val(c) >= 0.12 and cnt >= counts[0][0] * 0.3:
                dom = c
                break
    return avg, dom


def main():
    movies = json.loads((OUT / "data/movies.json").read_text(encoding="utf-8"))
    # 手动补图通道：用户把海报按 <电影名>_<年份>.jpg 放进 posters/ 后，这里自动收编
    adopted = 0
    for m in movies:
        if m.get("img"):
            continue
        cand = OUT / "posters" / safe_file(m["title"], m.get("year"))
        if cand.is_file():
            try:
                with Image.open(cand) as im:
                    w, h = im.size
                m["img"] = {"file": cand.name, "w": w, "h": h, "src": "manual", "title": m["title"]}
                adopted += 1
            except Exception:  # noqa: BLE001
                pass
    if adopted:
        (OUT / "data/movies.json").write_text(
            json.dumps(movies, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"手动补图收编: {adopted}")
    posters = []
    for m in movies:
        img = m.get("img")
        if not img:
            continue
        p = OUT / "posters" / img["file"]
        if not p.exists():
            continue
        avg, dom = analyze(p)
        posters.append({
            "file": "posters/" + img["file"],
            "title": m["title"],
            "year": m.get("year"),
            "rating": m.get("rating"),
            "star": bool(m.get("star")),
            "periods": m.get("periods", []),
            "douban": m.get("douban_id"),
            "doubanTitle": m.get("douban_title"),
            "avg": "#%02x%02x%02x" % avg,
            "dom": "#%02x%02x%02x" % dom,
            "mood": classify(dom),
            "w": img.get("w"), "h": img.get("h"),
        })

    sizes = Counter(p["mood"] for p in posters)
    for _ in range(4):  # 传递合并：绿→青→蓝 直到稳定
        sizes = Counter(p["mood"] for p in posters)
        changed = False
        for p in posters:
            mo = p["mood"]
            if sizes[mo] < MIN_POOL and mo in PARENTS:
                p["mood"] = PARENTS[mo]
                p["moodMerged"] = True
                changed = True
        if not changed:
            break

    sizes2 = Counter(p["mood"] for p in posters)
    moods = {k: [i for i, p in enumerate(posters) if p["mood"] == k]
             for k in sorted(sizes2, key=lambda k: -sizes2[k])}
    manifest = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "count": len(posters),
        "moods": moods,
        "posters": posters,
    }
    (OUT / "data/manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    # 顺手同步电视主题目录（themes/kd-55x9100h/posterwall/），theme.sh 直接可推——
    # 之前 manifest 与海报文件忘记同步主题目录吃过亏，这里自动化。
    for theme_parent in sorted((OUT / "themes").glob("*")):
        if not theme_parent.is_dir():
            continue
        theme = theme_parent / "posterwall"
        if True:
        theme.mkdir(exist_ok=True)
        (theme / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        (theme / "posters").mkdir(exist_ok=True)
        new = 0
        for p in posters:
            src = OUT / p["file"]
            dst = theme / p["file"]
            if not dst.is_file() and src.is_file():
                shutil.copy(src, dst)
                new += 1
        print(f"theme synced: {theme_parent.name} (+{new} new files)")
    print("posters:", len(posters))
    for k, v in moods.items():
        print(f"  {k}: {len(v)}")


if __name__ == "__main__":
    main()
