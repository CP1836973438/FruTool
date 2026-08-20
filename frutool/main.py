"""Application entry point — QML + Shader UI."""
from __future__ import annotations

import os
import sys

from frutool.gpu_policy import configure_startup

sys.argv = configure_startup(sys.argv)

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
if "--no-gpu-effects" in sys.argv:
    os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from frutool.bootstrap import create_qml_engine, load_app_window, qml_root
from frutool.config import init_runtime_dirs, resolve_app_icon_path
from frutool.demo import swap_demo_enabled
from frutool.demo.swap_demo import schedule_swap_demo
from frutool.demo.topo_demo import demo_enabled, schedule_topo_demo
from frutool.presentation.app import build_application


def _ensure_admin():
    """非管理员时自动 UAC 提权重启。"""
    if os.environ.get("FRUTOOL_SKIP_ADMIN") == "1":
        return
    if sys.platform != "win32":
        return
    import ctypes

    if ctypes.windll.shell32.IsUserAnAdmin():
        return
    params = " ".join(f'"{a}"' for a in sys.argv)
    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    if ret > 32:
        sys.exit(0)


def main():
    _ensure_admin()
    init_runtime_dirs()
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("FRU 自动化整合工具")
    app.setFont(QFont("Segoe UI", 10))

    icon_path = resolve_app_icon_path()
    if icon_path:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FruTool.FRUTool")
        app.setWindowIcon(QIcon(icon_path))

    app_root = build_application(app)
    app._frutool_root = app_root  # noqa: SLF001 — keep alive through quit teardown

    engine = create_qml_engine(app_root)
    app._frutool_engine = engine  # noqa: SLF001
    if not load_app_window(engine):
        print("Failed to load QML:", os.path.join(qml_root(), "AppWindow.qml"), file=sys.stderr)
        sys.exit(-1)

    root = engine.rootObjects()[0]
    if icon_path and hasattr(root, "setIcon"):
        root.setIcon(app.windowIcon())

    if demo_enabled():
        schedule_topo_demo(app_root)
    elif swap_demo_enabled():
        schedule_swap_demo(app_root)

    def _prepare_quit() -> None:
        for obj in engine.rootObjects():
            obj.setProperty("shuttingDown", True)
            if hasattr(obj, "hide"):
                obj.hide()
        QTimer.singleShot(0, app.quit)

    def _on_about_to_quit() -> None:
        for obj in list(engine.rootObjects()):
            obj.setProperty("shuttingDown", True)
        app.processEvents()
        app_root.controller.finalize_shutdown()

    app_root.controller.quitRequested.connect(_prepare_quit)
    app.aboutToQuit.connect(_on_about_to_quit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
