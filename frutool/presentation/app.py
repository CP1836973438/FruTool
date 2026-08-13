"""Build presentation layer root objects for QML registration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QObject

from frutool.presentation.controller import (
    ApplicationController,
    ChromeController,
    ConnController,
    OpsController,
    SwapController,
    TerminalController,
)
from frutool.presentation.viewmodels import (
    ChromeViewModel,
    ConnViewModel,
    DialogViewModel,
    FruViewModel,
    SwapViewModel,
    TerminalViewModel,
    TopoViewModel,
)


@dataclass
class ApplicationRoot:
    controller: ApplicationController
    conn: ConnController
    swap: SwapController
    ops: OpsController
    terminal: TerminalController
    chrome: ChromeController
    conn_vm: ConnViewModel
    swap_vm: SwapViewModel
    fru_vm: FruViewModel
    topo_vm: TopoViewModel
    terminal_vm: TerminalViewModel
    chrome_vm: ChromeViewModel
    dialog_vm: DialogViewModel

    @property
    def theme_bridge(self):
        return self.controller.themeBridge


def build_application(parent: Optional[QObject] = None) -> ApplicationRoot:
    ctrl = ApplicationController(parent)
    vm_parent: QObject = ctrl
    return ApplicationRoot(
        controller=ctrl,
        conn=ctrl.conn,
        swap=ctrl.swap,
        ops=ctrl.ops,
        terminal=ctrl.terminal,
        chrome=ctrl.chrome,
        conn_vm=ConnViewModel(ctrl.conn, vm_parent),
        swap_vm=SwapViewModel(ctrl.swap, vm_parent),
        fru_vm=FruViewModel(ctrl.ops, vm_parent),
        topo_vm=TopoViewModel(ctrl.ops, vm_parent),
        terminal_vm=TerminalViewModel(ctrl.terminal, vm_parent),
        chrome_vm=ChromeViewModel(ctrl.chrome, ctrl, vm_parent),
        dialog_vm=DialogViewModel(ctrl, vm_parent),
    )
