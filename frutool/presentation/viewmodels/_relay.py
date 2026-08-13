"""Signal relay helper for ViewModels."""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


def relay(src: QObject, src_name: str, dst: QObject, dst_signal: pyqtSignal) -> None:
    getattr(src, src_name).connect(dst_signal.emit)
