# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller --noconfirm --clean FRUTool.spec
# Output: dist/FRUTool/  (onedir — FRUTool.exe + _internal/ bundled resources)
# Override: place ipmitool/ (with ipmitool.exe + PcieEEpromTool.py) beside FRUTool.exe to replace bundled copy

import os
import sys

_icon = "FRUTool.ico"
_datas = [("frutool/qml", "frutool/qml")]

if os.path.isdir("ipmitool"):
    _datas.append(("ipmitool", "ipmitool"))
    if not os.path.isfile(os.path.join("ipmitool", "ipmitool.exe")):
        print(
            "WARNING: ipmitool/ipmitool.exe not found — build will continue, "
            "but packaged app needs external ipmitool unless provided at runtime.",
            file=sys.stderr,
        )
else:
    print(
        "WARNING: ipmitool/ directory not found — build will continue without bundled ipmitool.",
        file=sys.stderr,
    )

if os.path.isfile("PcieEEpromTool.py"):
    if os.path.isdir("ipmitool"):
        _datas.append(("PcieEEpromTool.py", "ipmitool"))
    else:
        print(
            "WARNING: PcieEEpromTool.py found but ipmitool/ missing — "
            "topology script will only be bundled inside ipmitool/.",
            file=sys.stderr,
        )
else:
    print(
        "WARNING: PcieEEpromTool.py not found — topology feature will need manual script beside exe.",
        file=sys.stderr,
    )

if os.path.isdir("PCLE"):
    _datas.append(("PCLE", "PCLE"))
else:
    print(
        "WARNING: PCLE/ directory not found — topology auto-match will need external PCLE beside exe.",
        file=sys.stderr,
    )

if os.path.isfile(_icon):
    _datas.insert(0, (_icon, "."))
_icon_arg = [_icon] if os.path.isfile(_icon) else []

a = Analysis(
    ['fru_tool.py'],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        # PyQt6
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtQml',
        'PyQt6.QtQuick',
        'PyQt6.QtWidgets',
        # App entry & config
        'frutool.main',
        'frutool.config',
        'frutool.bootstrap',
        'frutool.gpu_policy',
        # Presentation — app / controllers
        'frutool.presentation',
        'frutool.presentation.app',
        'frutool.presentation.controller',
        'frutool.presentation.controller.application',
        'frutool.presentation.controller.auto_swap_controller',
        'frutool.presentation.controller.auto_swap_session',
        'frutool.presentation.controller.auto_swap_workflow',
        'frutool.presentation.controller.base',
        'frutool.presentation.controller.chrome_controller',
        'frutool.presentation.controller.conn_controller',
        'frutool.presentation.controller.manual_swap_controller',
        'frutool.presentation.controller.network_controller',
        'frutool.presentation.controller.ops_controller',
        'frutool.presentation.controller.swap_controller',
        'frutool.presentation.controller.swap_progress',
        'frutool.presentation.controller.terminal_controller',
        # Presentation — dialogs / models / viewmodels
        'frutool.presentation.dialogs.file_dialogs',
        'frutool.presentation.models',
        'frutool.presentation.models.fru_field_model',
        'frutool.presentation.models.log_model',
        'frutool.presentation.models.network_model',
        'frutool.presentation.models.theme_bridge',
        'frutool.presentation.viewmodels',
        'frutool.presentation.viewmodels._relay',
        'frutool.presentation.viewmodels.chrome_vm',
        'frutool.presentation.viewmodels.conn_vm',
        'frutool.presentation.viewmodels.dialog_vm',
        'frutool.presentation.viewmodels.fru_vm',
        'frutool.presentation.viewmodels.swap_vm',
        'frutool.presentation.viewmodels.terminal_vm',
        'frutool.presentation.viewmodels.topo_vm',
        # Presentation — services
        'frutool.presentation.services',
        'frutool.presentation.services.capabilities_service',
        'frutool.presentation.services.credentials',
        'frutool.presentation.services.dialog_service',
        'frutool.presentation.services.fru_service',
        'frutool.presentation.services.ipmi_command_service',
        'frutool.presentation.services.log_presenter_service',
        'frutool.presentation.services.log_service',
        'frutool.presentation.services.manual_swap_service',
        'frutool.presentation.services.network_runtime_service',
        'frutool.presentation.services.network_service',
        'frutool.presentation.services.shell_service',
        'frutool.presentation.services.swap_auto_service',
        'frutool.presentation.services.swap_service',
        'frutool.presentation.services.terminal_service',
        'frutool.presentation.services.topo_service',
        # Domain
        'frutool.domain',
        'frutool.domain.backup',
        'frutool.domain.dhcp',
        'frutool.domain.fru_ops',
        'frutool.domain.ipmi',
        'frutool.domain.pcie_topo',
        'frutool.domain.topo_catalog',
        'frutool.domain.swap',
        'frutool.domain.swap.auto',
        'frutool.domain.swap.session',
        'frutool.domain.swap.status',
        # Infrastructure
        'frutool.infrastructure',
        'frutool.infrastructure.completions',
        'frutool.infrastructure.completions.cmd_line',
        'frutool.infrastructure.completions.ipmi_completions',
        'frutool.infrastructure.log_util',
        'frutool.infrastructure.network',
        'frutool.infrastructure.shell_runner',
        'frutool.infrastructure.workers',
        'py7zr',
        'rarfile',
        # Theme
        'frutool.theme',
        'frutool.theme.tokens',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FRUTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='fru_file_info.txt',
    icon=_icon_arg,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FRUTool',
)
