"""QtWidgets dialog adapters (isolated from QML view models)."""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QFileDialog

from frutool.config import BASE_DIR


def _dialog_parent():
    app = QApplication.instance()
    if app is None:
        return None
    return app.activeWindow()


def browse_topo_file(current_path: str) -> str:
    path, _ = QFileDialog.getOpenFileName(
        _dialog_parent(),
        "选择 PCIe 拓扑 .bin 文件",
        current_path or BASE_DIR,
        "Binary (*.bin);;All (*.*)",
    )
    return path or ""
