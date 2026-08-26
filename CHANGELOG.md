# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 6.0.0 — 2026-08-26

- 启动在 exe 旁自建 `PCLE/<厂商>/`，拓扑库同步到 `_internal/PCLE/` 加载；打包不再带出厂压缩包。卡片上的厂商/机型按厂家文件夹填写
- 换板克隆（手动与自动同一套逻辑）：始终还原新板 Board Serial；新旧主板 Board Part Number 不一致时再写回新板 PN
- FRU 字段页底部按钮与日志条增加间距
- 破坏性：现场拓扑库需自行放入 `PCLE/<厂商>/`，升级包不再内置出厂压缩包

## 5.5.1 — 2026-08-25

- 关于对话框与 exe 属性备注增加联系邮箱
- 文档：图文教程按「连接为公共第一步、其它功能并列」细化；导出 PDF（`docs/使用教程手册.pdf`）
- 破坏性：无

## 5.5.0 — 2026-08-20

- 拓扑页可下拉选择多版本 `PcieEEpromTool*.py`（扫描 exe / ipmitool / 内置），记住上次选择；刷写前将非 ipmitool 目录的脚本加载到 `ipmitool/PcieEEpromTool_run.py` 再执行
- 文档：新增现场《使用说明手册》（`docs/使用说明手册.md`）；另附图文教程与截图（`docs/使用教程手册.md` / `.html`）
- 破坏性：无

## 5.4.2 — 2026-08-20

- 换板备份识别同时接受手导的 `{SN}.bin` 与工具导出的 `{SN}_时间戳.bin`
- 破坏性：无

## 5.4.1 — 2026-08-20

- 换板演示不再自动填写 SN，只模拟 BMC 在线，便于手动输入验证跳过步骤 1
- 破坏性：无

## 5.4.0 — 2026-08-20

- 新增：换板演示环境（`FRUTOOL_DEMO_SWAP=1`），模拟 BMC 在线并投放无时间戳 `{SN}_manual.bin`，用于验证跳过阶段 1
- 破坏性：无

## [Unreleased]

### Added

- `README.md` — 项目说明、环境要求、构建与目录结构
- `CHANGELOG.md` — 版本变更记录
- `requirements-dev.txt` — 开发依赖（pytest、pytest-cov）
- `tests/` — Domain 层测试套件（97 个用例）
- `tests/conftest.py` — 共享 fixture 与 IPMI mock 工具
- `tests/test_ipmi.py` — FRU 解析、run_ipmi / probe 的 mock 测试
- `tests/test_fru_ops.py` — Step1/Step2 导出克隆流程 mock 测试
- `tests/test_swap_session.py` — 会话持久化与恢复逻辑测试
- `tests/test_backup.py` — FRU 备份文件列表测试
- `tests/test_swap_status.py` — 换板阶段状态文案测试
- `tests/test_pcie_topo.py` — 拓扑写入校验与 mock 测试
- `tests/test_dhcp.py` — DHCP 错误分类 helper 测试
- `.coveragerc` — Domain 覆盖率门槛 ≥ 80%（排除 OS 集成的 `dhcp.py`）

### Removed

- `_backend_original.py` — 重构前的单体后端快照（已由分层架构替代）
- `scripts/rebuild_application.py` — 从旧单体重建 ApplicationController 的脚本（已废弃）

### Changed

- `pyproject.toml` — 项目元数据、依赖、pytest 配置（替代 `pytest.ini`）
- `frutool/config.py` — 移除 import 时 `makedirs`，改为显式 `init_runtime_dirs()`
- `frutool/main.py` — 启动时调用 `init_runtime_dirs()`；Theme 仅通过 QML singleton 注册
- `frutool/qml/FruTool/Theme.qml` — 明确为 design-time stub，运行时由 ThemeBridge 注入
- `requirements.txt` / `requirements-dev.txt` — 指向 pyproject.toml 为 canonical 来源
- DHCP 门禁同步改为幂等更新，避免网卡轮询期间反复重启服务造成分配延迟
- DHCP 恢复监听全局广播地址，回复仍限定所选静态网卡并禁止不受限 fallback
- 静态网卡识别后立即启动 DHCP，不再等待链路 Up，覆盖 BMC 不定时启动场景
- 提高明暗主题文字对比度，浅色卡片改用亮色玻璃层级，并移除卡片 Hover 缩放
- 加强主导航页面切换的方向位移、淡入、轻缩放与溶解过渡

### Added

- `.github/workflows/ci.yml` — GitHub Actions（Ubuntu domain 测试 + Windows QML smoke）
- `frutool/bootstrap.py` — QML 引擎创建与 smoke 加载入口
- `frutool/qml/FruTool/dialogs/BaseDialog.qml` — 对话框公共骨架（标题 / 内容 / 分隔 / 按钮区）
- `tests/test_smoke.py` — QML 启动 smoke 与打包产物校验

### Added

- CI `package` job — Windows 全量 PyInstaller 打包并上传 `FRUTool.exe` artifact
- `scripts/verify_dist.ps1` — 校验打包产物存在且体积合理

### Removed

- `frutool/app/` — 遗留兼容层（已无引用，统一使用 `frutool.presentation`）

### Changed

- `FRUTool.spec` — 图标可选；补充 `frutool.bootstrap` hiddenimport
- 新增 `resolve_ipmitool_path()` 自动查找（含 `FRUTOOL_IPMITOOL` 环境变量与系统 PATH）
- `run_ipmi` 子进程 cwd / PATH 指向 ipmitool 所在目录，确保 DLL 依赖可加载

## [5.1.2.3] - 2026-06-23

### Changed

- 分层架构：Domain / Presentation / Infrastructure 模块划分
- PyQt6 + QML 界面，Controller / ViewModel 模式
- 自动换板流程：SN 确认、导出、轮询、克隆状态机

[Unreleased]: https://github.com/example/FruTool/compare/v5.1.2.3...HEAD
[5.1.2.3]: https://github.com/example/FruTool/releases/tag/v5.1.2.3
