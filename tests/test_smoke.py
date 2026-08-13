"""Smoke tests — QML bootstrap and packaging artifacts."""
from __future__ import annotations

import os

# Must be set before PyQt6 / QApplication initializes (Controls Windows plugin unavailable offscreen).
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.smoke
class TestQmlSmoke:
    def test_app_window_loads_offscreen(self):
        os.environ["FRUTOOL_SKIP_ADMIN"] = "1"
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
        os.environ.setdefault("FRUTOOL_SMOKE", "1")
        from frutool.bootstrap import smoke_load_qml

        smoke_load_qml()


@pytest.mark.smoke
class TestPackagingArtifacts:
    def test_entry_and_spec_exist(self):
        assert (ROOT / "fru_tool.py").is_file()
        assert (ROOT / "FRUTool.spec").is_file()

    def test_spec_references_core_assets(self):
        spec = (ROOT / "FRUTool.spec").read_text(encoding="utf-8")
        assert "fru_tool.py" in spec
        assert "frutool/qml" in spec

    def test_qml_entry_exists(self):
        assert (ROOT / "frutool" / "qml" / "FruTool" / "AppWindow.qml").is_file()

    def test_dialog_components_exist(self):
        dialogs = ROOT / "frutool" / "qml" / "FruTool" / "dialogs"
        for name in ("BaseDialog.qml", "MessageDialog.qml", "AboutDialog.qml", "SnConfirmDialog.qml"):
            assert (dialogs / name).is_file()

    def test_topo_qml_components_exist(self):
        components = ROOT / "frutool" / "qml" / "FruTool" / "components"
        for name in ("TopoCatalogGrid.qml", "TopoPickCard.qml"):
            assert (components / name).is_file()
        assert (ROOT / "frutool" / "qml" / "FruTool" / "pages" / "TopoPage.qml").is_file()

    def test_legacy_app_shim_removed(self):
        assert not (ROOT / "frutool" / "app").exists()
