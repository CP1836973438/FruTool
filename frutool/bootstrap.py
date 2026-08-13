"""QML bootstrap helpers shared by main() and smoke tests."""
from __future__ import annotations

import os
import sys

from PyQt6.QtCore import QUrl
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance


def qml_root() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "frutool", "qml", "FruTool")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml", "FruTool")


def create_qml_engine(app_root) -> QQmlApplicationEngine:
    """Register Theme singleton, ViewModels, and return a configured QML engine."""
    theme = app_root.theme_bridge
    qmlRegisterSingletonInstance("FruTool", 1, 0, "Theme", theme)

    engine = QQmlApplicationEngine()
    qml_base = os.path.join(qml_root(), os.pardir)
    engine.addImportPath(os.path.normpath(qml_base))
    ctx = engine.rootContext()
    ctx.setContextProperty("connVm", app_root.conn_vm)
    ctx.setContextProperty("swapVm", app_root.swap_vm)
    ctx.setContextProperty("fruVm", app_root.fru_vm)
    ctx.setContextProperty("topoVm", app_root.topo_vm)
    ctx.setContextProperty("terminalVm", app_root.terminal_vm)
    ctx.setContextProperty("chromeVm", app_root.chrome_vm)
    ctx.setContextProperty("dialogVm", app_root.dialog_vm)
    return engine


def load_app_window(engine: QQmlApplicationEngine) -> bool:
    qml_path = os.path.join(qml_root(), "AppWindow.qml")
    engine.load(QUrl.fromLocalFile(qml_path))
    return bool(engine.rootObjects())


def smoke_load_qml() -> None:
    """Smoke test entry: load AppWindow offscreen, then shut down."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    os.environ.setdefault("FRUTOOL_SMOKE", "1")
    from PyQt6.QtWidgets import QApplication

    from frutool.config import init_runtime_dirs
    from frutool.presentation.app import build_application

    init_runtime_dirs()
    app = QApplication([])
    app_root = build_application(app)
    engine = create_qml_engine(app_root)
    if not load_app_window(engine):
        raise RuntimeError(f"Failed to load QML: {os.path.join(qml_root(), 'AppWindow.qml')}")
    app.processEvents()
    app_root.controller.shutdown()
    app.processEvents()
