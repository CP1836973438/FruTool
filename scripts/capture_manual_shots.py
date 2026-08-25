#!/usr/bin/env python3
"""Capture FruTool UI screenshots for the illustrated user manual (demo mode)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    out_dir = root / "docs" / "images" / "manual"
    out_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("FRUTOOL_SKIP_ADMIN", "1")
    os.environ["FRUTOOL_DEMO_TOPO"] = "1"
    os.environ["FRUTOOL_DEMO_SCENARIO"] = "multi"
    os.environ.setdefault("FRUTOOL_DISABLE_GPU_EFFECTS", "1")

    sys.argv = [str(root / "fru_tool.py"), "--no-gpu-effects"]

    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QFont, QIcon
    from PyQt6.QtWidgets import QApplication

    from frutool.bootstrap import create_qml_engine, load_app_window
    from frutool.config import init_runtime_dirs, resolve_app_icon_path
    from frutool.demo.swap_demo import apply_swap_demo, seed_demo_backup
    from frutool.demo.topo_demo import apply_topo_demo
    from frutool.gpu_policy import configure_startup
    from frutool.presentation.app import build_application

    sys.argv = configure_startup(sys.argv)
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

    init_runtime_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName("FRU 自动化整合工具")
    app.setFont(QFont("Segoe UI", 10))
    icon_path = resolve_app_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    app_root = build_application(app)
    engine = create_qml_engine(app_root)
    if not load_app_window(engine):
        print("Failed to load QML", file=sys.stderr)
        return 1

    window = engine.rootObjects()[0]
    try:
        window.setProperty("width", 1180)
        window.setProperty("height", 820)
    except Exception:
        pass
    if icon_path and hasattr(window, "setIcon"):
        window.setIcon(app.windowIcon())

    shots: list[tuple[str, str]] = [
        ("conn", "01-conn.png"),
        ("fru", "02-fru.png"),
        ("main", "03-swap.png"),
        ("topo", "04-topo.png"),
    ]

    state = {"index": 0}

    def grab(name: str) -> None:
        img = window.grabWindow()
        path = out_dir / name
        ok = img.save(str(path), "PNG")
        print(f"{'OK' if ok else 'FAIL'}: {path} ({img.width()}x{img.height()})")

    def step() -> None:
        i = state["index"]
        if i == 0:
            # Shared demo connectivity + FRU hints + seed swap backup
            seed_demo_backup()
            apply_topo_demo(app_root, "multi")
            apply_swap_demo(app_root)
            app.processEvents()
            QTimer.singleShot(800, step)
            state["index"] = 1
            return

        shot_i = i - 1
        if shot_i >= len(shots):
            app.quit()
            return

        page, filename = shots[shot_i]
        app_root.chrome.showPage(page)
        app.processEvents()

        def after_paint() -> None:
            grab(filename)
            state["index"] = i + 1
            QTimer.singleShot(500, step)

        QTimer.singleShot(700, after_paint)

    # Wait for first show
    QTimer.singleShot(1200, step)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
