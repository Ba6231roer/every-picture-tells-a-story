# -*- coding: utf-8 -*-
"""电视适配度检测：这台电视能不能跑海报墙、有没有已知的坑。

用法：python tools/tv_check.py [--host 192.168.50.161:5555]
不传 --host 时自动取 `adb devices` 里的第一台。
"""
import argparse
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from common import Tv, find_adb, run  # noqa: E402

MIN_SDK = 26          # cleanyourtv launcher 的 minSdk
PKG = "com.gathin.tvhome"
issues = []


def check(name, ok, hint="", warn_only=False):
    mark = "✓" if ok else ("!" if warn_only else "✗")
    print(f"  {mark} {name}" + (f"  —— {hint}" if hint else ""))
    if not ok and not warn_only:
        issues.append(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None)
    args = ap.parse_args()

    adb = find_adb()
    if args.host:
        serial = args.host
    else:
        ok, out = run([adb, "devices"])
        devs = [l.split()[0] for l in out.splitlines()
                if l.strip() and not l.startswith(("List of", "*")) and "\tdevice" in l]
        if not devs:
            print("✗ 未发现设备：先 `adb connect <电视IP>:5555` 或插 USB")
            return 1
        serial = devs[0]
    tv = Tv(serial, adb)
    print(f"电视: {serial}")
    print("-" * 46)

    sdk = tv.prop("ro.build.version.sdk")
    check("Android 版本 ≥ 8.0（launcher minSdk 26）",
          sdk.isdigit() and int(sdk) >= MIN_SDK,
          f"当前 API {sdk or '?'}；cleanyourtv launcher 需要 ≥ {MIN_SDK}")
    abi = tv.prop("ro.product.cpu.abi")
    print(f"  ○ CPU ABI: {abi or '未知'}")

    # 启动器
    ok, out = tv.shell(f"pm path {PKG} 2>/dev/null | head -1")
    has_launcher = bool(out.strip())
    check("cleanyourtv 启动器已安装（com.gathin.tvhome）", has_launcher,
          "" if has_launcher else
          "未安装。到 cleanyourtv 项目安装（海报墙渲染需含 2026-10-24 之后改动，或打 patches/ 里的补丁）")

    # 默认桌面：query-activities 列出候选（解析在 Python 端做，避免设备端 grep 差异）
    _, homes_raw = tv.shell(
        "cmd package query-activities --brief -a android.intent.action.MAIN "
        "-c android.intent.category.HOME")
    candidates = sorted(set(re.findall(r"[\w.]+/[\w.]+", homes_raw)))
    candidates = [c for c in candidates if not c.startswith("com.android.tv.settings")]
    has_home_cand = any(PKG in c for c in candidates)
    check("桌面候选中有 cleanyourtv", has_home_cand,
          "候选: " + "；".join(candidates) if candidates else "无候选（未装任何桌面？）", warn_only=True)
    _, resumed_raw = tv.shell("dumpsys activity activities | grep -m1 ResumedActivity")
    mres = re.search(r"u0 ([\w.]+)/", resumed_raw)
    if PKG in (mres.group(1) if mres else ""):
        print("  ○ 当前前台即 cleanyourtv（海报墙桌面）")
    else:
        print("  ○ 当前前台不在桌面，默认桌面是否为 cleanyourtv 请肉眼确认")

    # 主题文件写入通道：部分固件锁 Android/data，需要走 /data/local/tmp 暂存
    test_file = f"/sdcard/Android/data/{PKG}/files/.epx_test"
    ok, out = tv.shell(f"echo t > '{test_file}' 2>/dev/null && ls '{test_file}' >/dev/null 2>&1 && rm -f '{test_file}' && echo WRITABLE")
    check("应用外部目录可写（主题/海报推送通道）", "WRITABLE" in out,
          "此固件锁了 Android/data（部分 TCL 等）：推送工具会自动走 /data/local/tmp 暂存写入，功能不受影响",
          warn_only=True)

    free = tv.free_space_mb()
    check("剩余空间 ≥ 100MB（海报包 ~15MB）", free < 0 or free >= 100, f"当前 {free}MB")
    print(f"  ○ 屏幕分辨率: {tv.screen() or '未知'}")

    print()
    if issues:
        print("不满足项：" + "；".join(issues))
    print("结论：" + ("此电视可运行海报墙 ✓" if sdk.isdigit() and int(sdk) >= MIN_SDK and has_launcher
                    else "还有不满足项，见上面的 ✗"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
