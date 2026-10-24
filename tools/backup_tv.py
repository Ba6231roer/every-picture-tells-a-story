# -*- coding: utf-8 -*-
"""一键备份电视上"可能被海报墙影响的东西"——本项目对电视只做三件事：
装/更新 cleanyourtv 启动器（可选）、写主题文件到应用外部目录、把启动器设为默认桌面。
全部可逆。此脚本把恢复所需的每一条信息存下来。

用法：python tools/backup_tv.py [--host 192.168.50.161:5555]
输出：backups/<时间戳>/（REPORT.md + home.txt + apps-3rd.txt + settings.txt + screen.png）
"""
import argparse
import datetime
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import Tv, find_adb, SHOTS, PKG  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None)
    args = ap.parse_args()
    serial = args.host
    adb = find_adb()
    if not serial:
        import subprocess
        r = subprocess.run([adb, "devices"], capture_output=True, text=True)
        devs = [l.split()[0] for l in r.stdout.splitlines()
                if l.strip() and not l.startswith(("List of", "*")) and "\tdevice" in l]
        if not devs:
            print("✗ 未发现设备")
            return 1
        serial = devs[0]
    tv = Tv(serial, adb)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = pathlib.Path("backups") / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    _, home = tv.shell(f"cmd package resolve-activity -c android.intent.category.HOME")
    _, launcher_apk = tv.shell(f"pm path {PKG} 2>/dev/null || true")
    _, apps3 = tv.shell("pm list packages -3")
    _, acc = tv.shell("settings get secure enabled_accessibility_services")
    _, acc_on = tv.shell("settings get secure accessibility_enabled")
    _, ver = tv.shell("getprop ro.build.version.release")
    _, sdk = tv.shell("getprop ro.build.version.sdk")
    _, screen = tv.shell("wm size")
    try:
        tv.run_adb(["-s", serial, "shell", "screencap -p /data/local/tmp/epx-shot.png"], timeout=30)
        tv.run_adb(["-s", serial, "pull", "/data/local/tmp/epx-shot.png",
                    str(out_dir / "screen-before.png")], timeout=30)
        tv.shell("rm -f /data/local/tmp/epx-shot.png")
    except Exception:  # noqa: BLE001
        pass

    (out_dir / "home.txt").write_text(home, encoding="utf-8")
    (out_dir / "launcher-apk-path.txt").write_text(launcher_apk, encoding="utf-8")
    (out_dir / "apps-3rd.txt").write_text(apps3, encoding="utf-8")
    (out_dir / "settings.txt").write_text(
        f"enabled_accessibility_services={acc}\naccessibility_enabled={acc_on}\n", encoding="utf-8")

    home_pkg = home.split("/")[-1].split(":")[0] if home else "?"
    report = f"""# 电视备份报告 — {stamp}

- 序列号: {serial}
- Android: {ver} (API {sdk})  分辨率: {screen}
- **当前默认桌面（最重要）**: `{home_pkg}`
  - 原始解析结果: `{home.strip()}`
- cleanyourtv 启动器: {('已装 ' + launcher_apk.strip()) if launcher_apk.strip() else '未安装'}
- 无障碍服务: `{acc}` (enabled={acc_on})

## 如何恢复（每条都能单独执行）

```bash
# 1) 恢复原默认桌面（若被改成别的）
adb -s {serial} shell cmd package set-home-activity --user 0 {home.strip().split('/')[0] + '/' + home.strip().split('/')[1] if '/' in home.strip() else home.strip()}

# 2) 彻底卸载海报墙所在启动器（卸载后系统自动回到原默认桌面）
adb -s {serial} uninstall {PKG}

# 3) 清掉主题/海报数据（卸载会自动删，这条是手动删）
adb -s {serial} shell rm -rf /sdcard/Android/data/{PKG}/files

# 4) 恢复无障碍服务（若用 cleanyourtv 的按键功能）
adb -s {serial} shell settings put secure enabled_accessibility_services '{acc}'
adb -s {serial} shell settings put secure accessibility_enabled {acc_on or 1}
```

> 本项目对电视的全部写入 = ① 一个普通应用（卸载即净）② 应用自己外部目录里的文件
> ③ 默认桌面设置项。不碰系统分区、不碰 root、不需要解锁。
"""
    (out_dir / "REPORT.md").write_text(report, encoding="utf-8")
    print(f"备份完成: {out_dir.resolve()}")
    print(f"  当前默认桌面: {home_pkg}")
    print("恢复命令见 REPORT.md")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
