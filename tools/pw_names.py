# -*- coding: utf-8 -*-
"""海报墙的统一文件名规则：`<电影名>_<上映年份>.jpg`（用户可读、可自替换）。

Windows 非法字符映射成全角（：／？等），电影名里的全角冒号本来就合法，保持原样。
所有产线脚本（rename_posters / build_manifest / merge_extension_results / fetch_posters_retry）
统一从这里取名，改规则只改这一处。
"""
import re

_TRANS = str.maketrans({
    "\\": "／", "/": "／", ":": "：", "*": "＊", "?": "？",
    '"': "＂", "<": "＜", ">": "＞", "|": "｜",
})


def safe_stem(title, year=None):
    t = (title or "").translate(_TRANS).strip().rstrip(". ")
    t = re.sub(r"\s+", " ", t)
    if not t:
        t = "untitled"
    return f"{t}_{year if year else '未知'}"


def safe_file(title, year=None):
    return safe_stem(title, year) + ".jpg"
