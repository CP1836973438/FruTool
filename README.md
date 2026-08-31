# FruTool — FRU 自动化整合工具

Windows 桌面工具，用于 BMC/IPMI 连接、FRU 读写、主板手动/自动换板、PCIe 拓扑 EEPROM 写入等现场硬件运维。

**当前版本：** 6.0.2

详细变更见 [CHANGELOG.md](CHANGELOG.md)。现场操作见 **[使用手册](docs/使用手册.md)**（Markdown 图文）或 **[使用说明手册](docs/使用说明手册.md)**（纯文字详版）。

## 功能概览

四个模块彼此独立。凡访问 BMC，须先完成 **连接与网络**；换板 / FRU / 拓扑无强制先后。

| 模块 | 说明 |
|------|------|
| **连接** | 本机网卡、内置 DHCP（专给 BMC 分地址）、在线探测、旧/新板凭据。底栏 BMC 地址变蓝后可开网页并复制对应密码 |
| **换板** | 旧板 FRU 备份 → 换板 → 克隆。始终还原新板 Board Serial；新旧主板 Board Part Number 不一致时再写回新板 PN。手动与自动同一套逻辑 |
| **FRU** | 连上 BMC 后字段框用灰字展示当前板 FRU；只刷写你新填的内容 |
| **拓扑** | 把 `.bin` 写入 EEPROM（0x7E00）。自己的文件放 exe 旁 `PCLE/<厂商>/`，程序同步到 `_internal/PCLE/` 再加载。打包不再带出厂压缩包 |
| **终端** | 底栏日志条展开右侧面板（全部 / DHCP / FRU / 拓扑）；底部可发 IPMI 或 Shell |

## 环境要求

- **操作系统：** Windows 10/11（需管理员权限，启动时自动 UAC 提权）
- **Python：** 3.10+（开发或打包版跑拓扑脚本时需要）
- **运行时依赖（非 pip）：**
  - `ipmitool/` — `ipmitool.exe`、`PcieEEpromTool.py` 及依赖
  - 也可通过环境变量 `FRUTOOL_IPMITOOL` 指定 exe 完整路径

**打包版资源查找顺序：** `FRUTOOL_IPMITOOL` → exe 同目录 `ipmitool/`（可覆盖）→ `_internal/ipmitool` 内置 → 系统 PATH

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 将 ipmitool 文件夹（含 ipmitool.exe 及依赖）放到项目根目录
python fru_tool.py
```

现场使用请运行打包目录里的 `FRUTool.exe`（整个 `FRUTool` 文件夹一起拷贝，不要只拷 exe）。

## 开发与测试

```powershell
pip install -r requirements-dev.txt

# Domain 单元测试（默认，含覆盖率门槛）
python -m pytest -v -m "not smoke"

# QML 启动 smoke test（需 PyQt6，Windows 推荐）
$env:QT_QPA_PLATFORM = "offscreen"
$env:FRUTOOL_SKIP_ADMIN = "1"
python -m pytest tests/test_smoke.py -v -m smoke
```

测换板流程须清掉 `FRUTOOL_DEMO_ALL` / `FRUTOOL_DEMO_SWAP`，否则会走演示桩。

## 打包发布

必须用**只装过 `requirements.txt`** 的纯净环境（推荐 `.venv-pack/`），不要拿日常混装过杂包的 `.venv` 打现场包。

```powershell
python -m venv .venv-pack
.\.venv-pack\Scripts\pip install -r requirements.txt
.\.venv-pack\Scripts\pyinstaller --clean --noconfirm FRUTool.spec
./scripts/verify_dist.ps1
```

发布物为 **`dist/FRUTool/` 整个文件夹**（含 `FRUTool.exe` 与 `_internal/`）。

- 拓扑脚本：放到 exe 旁 `ipmitool/` 即可覆盖内置，无需重打包
- 拓扑 `.bin`：放到 exe 旁 `PCLE/<厂商>/`（启动时自动建厂商目录），不要放进 `_internal/PCLE/`
- 打包校验会拒绝把出厂 zip/7z/rar 打进 `_internal/PCLE/`

## 目录结构

```
FruTool/
├── fru_tool.py              # 入口脚本
├── pyproject.toml           # 项目元数据与依赖
├── FRUTool.spec             # PyInstaller 配置
├── fru_file_info.txt        # exe 文件属性（版号随产品真源）
├── requirements.txt         # 运行时 + 打包依赖
├── requirements-dev.txt     # 开发依赖
├── frutool/                 # 应用（真源 __version__ 在 frutool/__init__.py）
├── docs/                    # 使用手册、架构与上下文
├── scripts/                 # 校验、演示、截图等
├── ipmitool/                # ipmitool 与拓扑脚本（开发源目录）
├── PCLE/                    # 运行时：用户投放拓扑库（按厂商子目录）
├── fru_backup/              # 运行时：FRU 备份与换板会话
└── logs/                    # 运行时：会话日志
```

## 架构

```
QML View  →  ViewModel  →  Controller  →  Service  →  Domain  →  Infrastructure
```

- **Domain 层** 保持纯 Python，便于单元测试
- **Presentation 层** 负责 Qt 信号槽、QML 绑定与后台任务调度
- **Infrastructure 层** 封装 subprocess、网络 IO、线程池

## 许可证

Copyright (c) 2026 CP Studio. All rights reserved.
