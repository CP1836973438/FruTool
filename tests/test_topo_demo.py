"""Tests for topology demo mode helpers."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from frutool.demo.topo_demo import (
    _demo_fru_hints,
    demo_enabled,
    resolve_scenario,
)


class TestTopoDemo:
    def test_demo_enabled_env(self, monkeypatch):
        monkeypatch.delenv("FRUTOOL_DEMO_TOPO", raising=False)
        assert demo_enabled() is False
        monkeypatch.setenv("FRUTOOL_DEMO_TOPO", "1")
        assert demo_enabled() is True

    def test_resolve_scenario_multi(self):
        scenario = resolve_scenario("multi")
        assert scenario.product_extra == "Suite:M51M1-I9DD2M"
        assert scenario.product_manufacturer == "Inspur"

    def test_unknown_scenario(self):
        with pytest.raises(ValueError, match="未知演示场景"):
            resolve_scenario("nope")

    def test_demo_fru_hints_include_suite(self):
        scenario = resolve_scenario("multi")
        hints = _demo_fru_hints(scenario)
        assert hints["Product Extra"] == "Suite:M51M1-I9DD2M"
        assert hints["Product Manufacturer"] == "Inspur"


class TestApplyTopoDemo:
    def test_replaces_frozen_network_config(self, qapp, monkeypatch):
        from frutool.demo.topo_demo import apply_topo_demo
        from frutool.presentation.app import build_application

        monkeypatch.setenv("FRUTOOL_DEMO_TOPO", "1")
        app_root = build_application(qapp)
        scenario = apply_topo_demo(app_root, "multi")
        assert app_root.conn.bmc_ip == scenario.bmc_ip
        assert app_root.conn.bmcOnline is True
        assert app_root.chrome.currentPage == "topo"

    def test_topo_demo_qml_loads_offscreen(self, qapp, monkeypatch):
        from frutool.bootstrap import create_qml_engine, load_app_window
        from frutool.demo.topo_demo import apply_topo_demo
        from frutool.presentation.app import build_application

        monkeypatch.setenv("FRUTOOL_DEMO_TOPO", "1")
        monkeypatch.setenv("FRUTOOL_SKIP_ADMIN", "1")
        monkeypatch.setenv("FRUTOOL_SMOKE", "1")
        app_root = build_application(qapp)
        apply_topo_demo(app_root, "multi")
        engine = create_qml_engine(app_root)
        assert load_app_window(engine)
