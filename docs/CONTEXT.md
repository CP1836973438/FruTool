# 项目上下文

更新：2026-08-25

## 当前目标
- 5.5.1 已本地可交付：关于联系邮箱；图文教程/PDF；产物在 `dist/FRUTool/`

## 已拍板
- 拓扑多脚本下拉 + 刷写前加载进 `ipmitool/PcieEEpromTool_run.py`
- 联系邮箱放关于对话框（及 exe Comments），不进版权行：`CP1836973438@outlook.com`
- 手册结构：连接为唯一公共第一步；换板 / FRU / 拓扑为并列第二步

## 踩过的坑
- 绝对路径跑拓扑脚本现场不可靠 → 必须加载进 ipmitool
- 打包时若 `dist/FRUTool` 被占用，可临时 `--distpath dist_551` 再挪回

## 未决 / 下一步
- 总控是否同意 5.5.1 推 GitHub / 挂 Release Assets
