# -*- coding: utf-8 -*-
"""环境检测：开发机侧需要什么、缺什么、怎么补。

用法：python tools/env_check.py
"""
import importlib
import shutil
import sys
import pathlib

OK, BAD, OPT = "✓", "✗", "○"
missing_hard = []


def check(name, ok, hint="", optional=False):
    mark = OK if ok else (OPT if optional else BAD)
    print(f"  {mark} {name}" + (f"  —— {hint}" if hint and not ok else ""))
    if not ok and not optional:
        missing_hard.append(name)


def main():
    print("开发机环境")
    print("-" * 46)
    v = sys.version_info
    check("Python ≥ 3.9", v >= (3, 9), f"当前 {v.major}.{v.minor}，请安装 3.9+")
    try:
        importlib.import_module("PIL")
        check("Pillow（颜色分析）", True)
    except ImportError:
        check("Pillow（颜色分析）", False, "pip install pillow")
    check("adb（platform-tools）", bool(shutil.which("adb")) or
          pathlib.Path("C:/DEV/android/sdk/platform-tools/adb.exe").is_file(),
          "安装 Android platform-tools，或 set ADB=<路径>")
    check("ffmpeg（转 GIF/WebP，可选）", bool(shutil.which("ffmpeg")), "winget install Gyan.FFmpeg", optional=True)
    check("scrcpy（流畅录屏，可选）", bool(shutil.which("scrcpy")), "winget install Genymobile.scrcpy", optional=True)
    check("Chrome + 海报墙插件（抓海报）", pathlib.Path(__file__).resolve().parent.parent.joinpath("extension/manifest.json").is_file(),
          "见 extension/README.md")
    print()
    print("结果：" + ("全部就绪 ✓" if not missing_hard else
                    "缺少必需项: " + ", ".join(missing_hard)))
    return 0 if not missing_hard else 1


if __name__ == "__main__":
    sys.exit(main())
