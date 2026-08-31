# 项目上下文

更新：2026-08-31

## 当前目标
- 总控同意把 **6.0.1** 推 GitHub：更新 README，不跟踪 `.github/workflows` 与 `.vscode`，打标签并挂 Release Assets。

## 已拍板
- 拓扑多脚本下拉 + 刷写前加载进 `ipmitool/PcieEEpromTool_run.py`
- 联系邮箱放关于对话框（及 exe Comments），不进版权行：`CP1836973438@outlook.com`
- 手册结构：连接为唯一公共第一步；换板 / FRU / 拓扑为并列第二步
- 底栏蓝色 BMC 地址：单击打开 `http://IP`，并用 IPMI 试旧/新板凭据后复制对应密码
- 内置 DHCP 专为 BMC：因网上深度远程启动管理器偶发卡住、不分配地址而做；与网深互斥（UDP 67）
- 终端：底栏日志条展开右侧面板；标签全部/DHCP/FRU/拓扑；底部可发 IPMI 或 Shell
- 自己的拓扑 `.bin` 放 exe 旁 `PCLE/<厂商>/`，同步到 `_internal/PCLE/` 加载。不打包出厂压缩包。卡片厂商按厂家文件夹填写
- 换板克隆（手动/自动同一 `run_step2_clone`）：始终还原新板 Board Serial；Board Part Number 不一致时再写回新板 PN
- FRU 页：BMC 在线后自动读当前板 FRU，字段框灰字展示现有值；只刷用户新填的内容
- GitHub 不收录 `.github/workflows` 与 `.vscode`（本地可留着，`.gitignore` 忽略）

## 踩过的坑
- 绝对路径跑拓扑脚本现场不可靠 → 必须加载进 ipmitool
- 打包时若 `dist/FRUTool` 被占用，可临时换 `--distpath` 再挪回
- 全功能演示里假 BMC 一直在线，自动换板 wait_swap/wait_new 必须走演示桩，否则卡死
- 测换板流程须清掉 `FRUTOOL_DEMO_ALL` / `FRUTOOL_DEMO_SWAP`，否则会走演示桩
- GitHub 此前只有 Initial commit；5.5.0～6.0.0 一直只在本地

## 未决 / 下一步
- 推送后核对：README 为 6.0.1、标签 `v6.0.1`、Release Assets 能下载现场包
