# FruTool — FRU 自动化整合工具

Windows 桌面工具，用于 BMC/IPMI 连接、FRU 读写、主板自动/手动换板、PCIe 拓扑 EEPROM 写入等硬件运维场景。

**当前版本：** 5.5.0

## 功能概览

| 模块 | 说明 |
|------|------|
| **连接** | BMC 网络配置、DHCP 服务、在线探测、凭据管理 |
| **FRU** | 读取 / 批量写入 FRU 字段、备份与恢复 |
| **换板** | 自动换板流程（SN 确认 → 导出 → 轮询 → 克隆）；手动换板 Step1/Step2 |
| **拓扑** | PCIe 拓扑 EEPROM：PCLE 压缩包 + 散落 .bin 索引与刷写 |
| **终端** | 内置 IPMI 命令终端与补全 |

现场操作请先看 **[使用说明手册](docs/使用说明手册.md)**（连接、换板、拓扑脚本选择与注意点）。

## 环境要求

- **操作系统：** Windows 10/11（需管理员权限，启动时自动 UAC 提权）
- **Python：** 3.10+
- **运行时依赖（非 pip）：**
  - `ipmitool/` 目录 — 内含 `ipmitool.exe`、`PcieEEpromTool.py` 及其依赖文件（开发/打包源目录）
  - 也可通过环境变量 `FRUTOOL_IPMITOOL` 指定 exe 完整路径

**打包版资源查找顺序：** `FRUTOOL_IPMITOOL` → exe 同目录 `ipmitool/`（可覆盖）→ `_internal/ipmitool` 内置 → 系统 PATH

## 快速开始

```powershell
# 1. 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖（任选其一）
pip install -r requirements.txt
# 或从 pyproject.toml 安装（推荐）
pip install -e .

# 3. 将 ipmitool 文件夹（含 ipmitool.exe 及依赖）放到项目根目录
# 4. 启动
python fru_tool.py
```

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

## 打包发布

```powershell
# 编译 QML 着色器（修改 .frag 后需要）
.\scripts\compile_shaders.ps1

# 确保项目根目录存在 ipmitool/（含 ipmitool.exe）；PcieEEpromTool.py 放在 ipmitool/ 或项目根（打包时复制进 ipmitool/）

# PyInstaller 打包（onedir → dist/FRUTool/）
pyinstaller --noconfirm --clean FRUTool.spec
./scripts/verify_dist.ps1
```

发布物为 **`dist/FRUTool/` 整个文件夹**（含 `FRUTool.exe` 与 `_internal/`）。  
更换 ipmitool 或拓扑脚本时，可将新版放在 **exe 同目录** 覆盖内置，无需重打包。

## 目录结构

```
FruTool/
├── fru_tool.py              # 入口脚本
├── pyproject.toml           # 项目元数据与依赖（canonical）
├── FRUTool.spec             # PyInstaller 配置
├── requirements.txt         # 运行时依赖（指向 pyproject.toml）
├── requirements-dev.txt     # 开发依赖（editable + dev extras）
├── frutool/
│   ├── main.py              # 应用启动（QML 引擎、ViewModel 注册）
│   ├── config.py            # 常量、路径、超时配置
│   ├── domain/              # 业务逻辑（无 Qt 依赖）
│   ├── presentation/        # Controller / ViewModel / Service / QML 桥接
│   ├── infrastructure/      # 网络、Worker、Shell、日志
│   ├── theme/               # 设计 token
│   └── qml/FruTool/         # QML 界面（pages / components / dialogs）
├── scripts/
│   ├── compile_shaders.ps1  # GLSL → .qsb 编译
│   └── verify_dist.ps1      # PyInstaller 产物校验
├── .github/workflows/ci.yml # GitHub Actions CI
├── fru_backup/              # FRU 备份与换板会话（运行时生成）
└── logs/                    # 会话日志（运行时生成）
```

## 架构

```
QML View  →  ViewModel  →  Controller  →  Service  →  Domain  →  Infrastructure
```

- **Domain 层** 保持纯 Python，便于单元测试（如 `domain/swap/auto.py`）
- **Presentation 层** 负责 Qt 信号槽、QML 绑定与后台任务调度
- **Infrastructure 层** 封装 subprocess、网络 IO、线程池

## 运行时数据

| 路径 | 用途 |
|------|------|
| `fru_backup/` | FRU bin 备份、换板会话 JSON、网卡 IP 备份 |
| `logs/` | 按日期滚动的会话日志 |

## 许可证

Copyright (c) 2026 CP Studio. All rights reserved.
