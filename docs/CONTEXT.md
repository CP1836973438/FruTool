# 项目上下文

更新：2026-08-26

## 当前目标
- 6.0.0 已本地归档：PCLE 厂家目录 + 换板按 PN 决定是否写回新板 PN。未推 GitHub。

## 已拍板
- 拓扑多脚本下拉 + 刷写前加载进 `ipmitool/PcieEEpromTool_run.py`
- 联系邮箱放关于对话框（及 exe Comments），不进版权行：`CP1836973438@outlook.com`
- 手册结构：连接为唯一公共第一步；换板 / FRU / 拓扑为并列第二步
- 底栏蓝色 BMC 地址：单击打开 `http://IP`，并用 IPMI 试旧/新板凭据后复制对应密码
- 内置 DHCP 专为 BMC：因网上深度远程启动管理器偶发卡住、不分配地址而做；与网深互斥（UDP 67）
- 终端：底栏日志条展开右侧面板；标签全部/DHCP/FRU/拓扑；底部可发 IPMI 或 Shell
- 自己的拓扑 `.bin` 放 exe 旁 `PCLE/<厂商>/`，同步到 `_internal/PCLE/` 加载。不打包出厂压缩包。卡片厂商按厂家文件夹填写
- 换板克隆（手动/自动同一 `run_step2_clone`）：始终还原新板 Board Serial；Board Part Number 不一致时再写回新板 PN

## 踩过的坑
- 绝对路径跑拓扑脚本现场不可靠 → 必须加载进 ipmitool
- 打包时若 `dist/FRUTool` 被占用，可临时 `--distpath dist_551` 再挪回
- 全功能演示里假 BMC 一直在线，自动换板 wait_swap/wait_new 必须走演示桩，否则卡死
- 测换板流程须清掉 `FRUTOOL_DEMO_ALL` / `FRUTOOL_DEMO_SWAP`，否则会走演示桩

## 未决 / 下一步
- 总控是否同意 6.0.0 推 GitHub / 挂 Release Assets（需按 6.0.0 重打包）
- README 仍写 5.5.1，上 GitHub 前再改成 6.0.0
