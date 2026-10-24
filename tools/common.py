# -*- coding: utf-8 -*-
"""共享工具：项目路径、adb 发现、设备连接与基础操作。

所有 tools/ 下的脚本都 import 这里，保证:
- 路径相对项目根（独立项目，不依赖任何本地绝对路径）;
- adb 从环境变量 ADB 或 PATH 或常见安装位置自动发现;
- 对电视的所有写操作都走 "push 到 /data/local/tmp 暂存 + shell cp 到目标"，
  以兼容把 shell 锁在 Android/data 之外的固件（部分 TCL 等）。
"""
import os
import shutil
import subprocess
import sys
import time
import pathlib

PROJECT = pathlib.Path(__file__).resolve().parent.parent
POSTERS = PROJECT / "posters"
DATA = PROJECT / "data"
THEMES = PROJECT / "themes"
SHOTS = PROJECT / "shots"
PKG = "com.gathin.tvhome"          # cleanyourtv 启动器的包名
TV_FILES = f"/sdcard/Android/data/{PKG}/files"
STAGE = "/data/local/tmp/epx"

_COMMON_HINT = "未找到 adb。安装 Android platform-tools，或 set ADB=<adb.exe 路径>"


def find_adb():
    """按优先级发现 adb：环境变量 > PATH > 常见安装位置。"""
    env = os.environ.get("ADB")
    if env and pathlib.Path(env).is_file():
        return env
    if shutil.which("adb"):
        return "adb"
    for cand in (
        pathlib.Path("C:/DEV/android/sdk/platform-tools/adb.exe"),
        pathlib.Path.home() / "AppData/Local/Android/Sdk/platform-tools/adb.exe",
        pathlib.Path.home() / "AppData/Local/Android/Sdk/platform-tools/adb",
    ):
        if cand.is_file():
            return str(cand)
    print("✗ " + _COMMON_HINT)
    sys.exit(1)


def run(args, timeout=60, capture=True):
    """跑一条命令，返回 (ok, stdout)。"""
    try:
        r = subprocess.run(args, capture_output=capture, text=True,
                           timeout=timeout, errors="replace")
        return r.returncode == 0, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except FileNotFoundError as e:
        return False, str(e)


class Tv:
    """一台通过 adb 连接的电视。serial 形如 192.168.50.161:5555 或 USB 序列号。"""

    def __init__(self, serial, adb=None):
        self.adb = adb or find_adb()
        self.serial = serial
        if ":" in serial:  # 网络设备需要 connect
            self.run_adb(["connect", serial])

    def run_adb(self, args, timeout=30):
        ok, out = run([self.adb] + args, timeout=timeout)
        return ok, out

    def shell(self, cmd, timeout=60):
        ok, out = self.run_adb(["-s", self.serial, "shell", cmd], timeout=timeout)
        return ok, out.strip()

    def push(self, local: pathlib.Path, remote: str, timeout=120):
        """push 到暂存区再 cp 到目标（目标可含中文/空格；绕开 Android/data 限制）。"""
        ok, out = self.run_adb(["-s", self.serial, "push", str(local),
                                f"{STAGE}/stage{int(time.time() * 1000) % 100000}"], timeout=timeout)
        if not ok:
            raise RuntimeError("adb push 失败: " + out[:200])
        staged = out.strip().splitlines()[-1].strip() if out.strip() else ""
        # scrcpy/adb 各版本输出不同：直接取推送目标路径
        if not staged.startswith("/"):
            staged = out.strip().splitlines()[-1].strip()
        ok, out = self.shell(f"cp '{staged}' '{remote}'", timeout=timeout)
        self.shell(f"rm -f '{staged}'")
        if not ok:
            raise RuntimeError(f"cp 到 {remote} 失败: {out[:200]}")
        return True

    def push_text(self, text: str, remote: str):
        """小文本文件：直接 shell 写入（免 push 往返）。"""
        ok, out = self.shell(f"echo '{self._q(text)}' > '{remote}'")
        if not ok:
            raise RuntimeError(f"写入 {remote} 失败: {out[:200]}")

    @staticmethod
    def _q(s):
        return s.replace("'", "'\\''")

    # ---- 常用只读查询 ----

    def prop(self, name):
        ok, out = self.shell(f"getprop {name}")
        return out.strip() if ok else ""

    def default_home(self):
        ok, out = self.shell(
            "cmd package resolve-activity -c android.intent.category.HOME | grep -m1 name= || true")
        return out.strip()

    def free_space_mb(self, path="/sdcard"):
        ok, out = self.shell(f"df -k {path} | tail -1")
        try:
            return int(out.split()[3]) // 1024
        except (IndexError, ValueError):
            return -1

    def screen(self):
        ok, out = self.shell("wm size")
        return out.replace("Physical size:", "").strip() if ok else "?"
