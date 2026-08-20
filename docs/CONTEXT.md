# 项目上下文

更新：2026-08-20

## 当前目标
- 5.5.0 已本地可交付：拓扑多脚本下拉 + 刷写前加载进 ipmitool；使用说明手册已写；产物在 `dist/FRUTool/`

## 已拍板
- 拓扑脚本下拉扫描 `PcieEEpromTool*.py`（exe / ipmitool / 内置），记住上次选择（`logs/topo_prefs.json`）
- 脚本必须在 ipmitool 下才能跑；其它位置选中后复制为 `ipmitool/PcieEEpromTool_run.py` 再执行（不覆盖主脚本）
- 现场手册：`docs/使用说明手册.md`

## 踩过的坑
- 仅用绝对路径 + cwd=ipmitool 在现场不可靠 → 必须加载进 ipmitool 目录
- PowerShell `Add-Content` 写入含 · 的测试文件易坏编码 → 用 Python UTF-8 写文件

## 未决 / 下一步
- 总控是否同意 5.5.0 推 GitHub / 挂 Release Assets
- README 仍偏开发向；现场以使用说明手册为准
