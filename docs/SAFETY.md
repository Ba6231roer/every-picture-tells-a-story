# 电视安全：备份、可逆性与恢复

这个项目最容易被担心的问题："会不会搞坏我的电视"。先把结论放在最前面：

> **本项目对电视的全部写入只有三样，全部可逆，逐条列出：**

| # | 写入内容 | 性质 | 如何撤销 |
|---|---|---|---|
| 1 | cleanyourtv 启动器（一个普通应用） | 非系统应用，装在用户分区 | `adb uninstall com.gathin.tvhome`，卸载后系统自动回到原默认桌面 |
| 2 | 主题与海报文件 | 写在该应用**自己的外部存储目录**（`/sdcard/Android/data/com.gathin.tvhome/files/`） | 删除该目录即可，卸载应用时也会自动删除 |
| 3 | 默认桌面设置项（一条系统设置） | `cmd package set-home-activity` | `cmd package set-home-activity --user 0 <原桌面组件>`（备份文件里有你电视的准确命令） |

**不碰系统分区、不需要 root、不需要解锁 bootloader、不改任何系统应用。**

## 开始前：一键备份

```bash
python tools/backup_tv.py --host 电视IP:5555
```

会生成 `backups/<时间戳>/`：

- `REPORT.md` —— 恢复命令清单（**每条都能单独复制执行**，含你电视的准确组件名）
- `home.txt` —— 当前默认桌面（最重要的恢复信息）
- `apps-3rd.txt` —— 已装第三方应用列表
- `settings.txt` —— 无障碍服务设置
- `screen-before.png` —— 改动前屏幕截图

## 恢复场景速查

| 场景 | 恢复方法 |
|---|---|
| 不想要海报墙了 | `adb uninstall com.gathin.tvhome` → 自动回到原默认桌面 |
| 只想换回原桌面、保留应用 | 用 REPORT.md 里的 `set-home-activity` 命令 |
| 海报/主题出问题 | 删除 `files/posterwall/` 目录，重启 Home |
| 启动器闪退 | 卸载重装（数据不受影响） |

## 已知边界（诚实清单）

- **Android/data 锁**：部分固件（TCL 部分型号等）把 shell 锁在 Android/data 之外。
  推送工具会自动检测并退回 `/data/local/tmp` 暂存 + `content` 写入的方案，
  `tools/tv_check.py` 会提前告诉你这台电视是哪种情况；
- **录屏帧率**：电视端 H.264 编码器较弱，`screenrecord` 只有 ~5fps；本项目用
  scrcpy 录制约 14fps，够动图用，但别期待 60fps 录屏；
- **4K 电视的 UI 分辨率**：多数电视系统 UI 跑在 1080p，海报墙随系统分辨率走，
  海报源图 270px 宽在 1080p 下观感良好。
