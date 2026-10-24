# -*- coding: utf-8 -*-
"""把主题（config.json + 默认海报包）推送到电视，并重启 Home 生效。

用法：python tools/push_theme.py [--theme themes/example-kd55x9100h] [--host IP:PORT]

等价于 cleanyourtv 的 tools/theme.sh，但只依赖 adb（不依赖 cleanyourtv 仓库）。
所有写入都走 /data/local/tmp 暂存 + cp，兼容锁 Android/data 的固件。
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import Tv, find_adb, PROJECT, PKG  # noqa: E402

RESTART = ("a=$(settings get secure enabled_accessibility_services); "
           f"am force-stop {PKG}; am start -n {PKG}/.MainActivity >/dev/null; "
           "case \"$a\" in *com.gathin.tvhome*) sleep 1; "
           "settings put secure enabled_accessibility_services ''; "
           "settings put secure accessibility_enabled 0; sleep 1; "
           "settings put secure enabled_accessibility_services \"$a\"; "
           "settings put secure accessibility_enabled 1 ;; esac")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="themes/example-kd55x9100h")
    ap.add_argument("--host", default=None)
    args = ap.parse_args()

    theme = pathlib.Path(args.theme)
    if not theme.is_absolute():
        theme = PROJECT / theme
    cfg = theme / "config.json"
    if not cfg.is_file():
        print(f"✗ 找不到 {cfg}")
        return 1
    json.loads(cfg.read_text(encoding="utf-8"))  # 校验 JSON

    # 海报来源：主题目录里的 posterwall/ 若存在则用之，否则用项目默认海报包
    src_manifest = theme / "posterwall" / "manifest.json"
    if not src_manifest.is_file():
        src_manifest = PROJECT / "data" / "manifest.json"
    posters_dir = PROJECT / "posters"
    if not src_manifest.is_file():
        print("✗ 缺 manifest.json（先跑 tools/build_manifest.py）")
        return 1

    adb = find_adb()
    serial = args.host
    if not serial:
        import subprocess
        r = subprocess.run([adb, "devices"], capture_output=True, text=True)
        devs = [l.split()[0] for l in r.stdout.splitlines()
                if l.strip() and not l.startswith(("List of", "*")) and "\tdevice" in l]
        if not devs:
            print("✗ 未发现设备：adb connect <IP>:5555 或插 USB")
            return 1
        serial = devs[0]
    tv = Tv(serial, adb)
    files = f"/sdcard/Android/data/{PKG}/files"

    print(f"电视: {serial}")
    tv.shell(f"mkdir -p '{files}/posterwall/posters' '{files}/wallpapers'")

    # 1) config.json
    tv.push(cfg, f"{files}/config.json")
    print("  config.json ✓")

    # 2) manifest + 海报（先清旧图；推送用序号别名暂存，电视端 cp 成中文名）
    tv.shell(f"rm -f '{files}/posterwall/manifest.json' "
             f"'{files}/posterwall/posters/'*.jpg 2>/dev/null; true")
    tv.push(src_manifest, f"{files}/posterwall/manifest.json")
    manifest = json.loads(src_manifest.read_text(encoding="utf-8"))
    n = 0
    for i, p in enumerate(manifest["posters"]):
        name = pathlib.Path(p["file"]).name
        local = PROJECT / p["file"]
        if not local.is_file():
            continue
        tv.push(local, f"/data/local/tmp/epx-poster-{i}.jpg")
        tv.shell(f"cp '/data/local/tmp/epx-poster-{i}.jpg' "
                 f"'{files}/posterwall/posters/{name}' && "
                 f"rm -f '/data/local/tmp/epx-poster-{i}.jpg'")
        n += 1
        if n % 50 == 0:
            print(f"  海报 {n}…")
    print(f"  海报 {n} 张 ✓")

    # 3) 重启 Home（保留无障碍服务）
    tv.shell(RESTART, timeout=90)
    print(f"完成：主题 {theme.name} 已生效。共 {manifest['count']} 部海报。")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
