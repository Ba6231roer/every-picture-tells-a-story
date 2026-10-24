# -*- coding: utf-8 -*-
"""把 Chrome 插件抓到的海报合并进海报墙。

用法：
  python tools/merge_extension_results.py [results.json 的路径]
  （海报 jpg 在  <下载目录>/poster-wall/，results.json 由插件的"导出结果"生成）

做三件事：
  1. results.json 里成功的条目 -> 把 Downloads/poster-wall/<doubanId>.jpg 复制为
     posters/m<md5(片名)>.jpg（海报墙的统一命名）；
  2. 更新 data/movies.json：对应电影的 img 记为 {file, src: "douban_ext", title: 豆瓣片名}；
  3. 提示跑 build_manifest.py 重建 manifest，然后 tools/theme.sh 重新推送电视。
图片尺寸/合法性在合并时用 Pillow 校验，明显横图（宽>高*1.35，豆瓣海报都是竖版）跳过。
"""
import json
import sys
import pathlib
from PIL import Image
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pw_names import safe_file  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent
DOWNLOADS = pathlib.Path.home() / "Downloads" / "poster-wall"


def main():
    results_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not results_path:
        cands = sorted(DOWNLOADS.parent.glob("**/poster-wall/results.json"), key=lambda p: p.stat().st_mtime)
        results_path = cands[-1] if cands else None
    if not results_path or not results_path.is_file():
        print("找不到 results.json（先在插件里点\"导出结果\"，或把路径作为参数传入）")
        return
    results = json.loads(results_path.read_text(encoding="utf-8"))
    done = results.get("done", [])
    print(f"results.json: {len(done)} 成功 / {len(results.get('failed', []))} 失败")

    movies = json.loads((OUT / "data/movies.json").read_text(encoding="utf-8"))
    by_title = {m["title"].casefold(): m for m in movies}
    copied = skipped = 0
    for r in done:
        m = by_title.get((r.get("title") or "").casefold())
        if not m:
            skipped += 1
            continue
        src = DOWNLOADS / (r.get("file") or "")
        if not src.is_file():
            skipped += 1
            continue
        try:
            with Image.open(src) as im:
                w, h = im.size
                if w > h * 1.35 or w < 60:
                    print(f"  跳过（形状不像海报 {w}x{h}）: {m['title']}")
                    skipped += 1
                    continue
                dest = OUT / "posters" / safe_file(m["title"], m.get("year"))
                im.convert("RGB").save(dest, "JPEG", quality=88)
        except Exception as e:  # noqa: BLE001
            print(f"  跳过（图片打不开）: {m['title']} {e}")
            skipped += 1
            continue
        m["img"] = {"file": dest.name, "w": w, "h": h, "src": "douban_ext",
                    "title": r.get("doubanTitle") or m["title"], "url": ""}
        m["douban_id"] = r.get("doubanId")
        copied += 1
    (OUT / "data/movies.json").write_text(
        json.dumps(movies, ensure_ascii=False, indent=1), encoding="utf-8")
    miss = [m for m in movies if not m.get("img")]
    (OUT / "data/misses.json").write_text(json.dumps(miss, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"合并完成：新海报 {copied} 张，跳过 {skipped}，当前 {sum(1 for m in movies if m.get('img'))}/{len(movies)}")
    print("下一步：python tools/build_manifest.py && 推电视：TV_HOST=192.168.50.161 tools/theme.sh themes/kd-55x9100h")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
