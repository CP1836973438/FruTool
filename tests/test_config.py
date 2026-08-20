"""Tests for application config."""
from __future__ import annotations

import frutool.config as config_mod
from frutool.config import (
    get_ipmitool_dir,
    get_ipmitool_path,
    init_runtime_dirs,
    list_pcie_eeprom_tools,
    load_topo_script_pref,
    resolve_ipmitool_path,
    resolve_pcie_eeprom_tool,
    save_topo_script_pref,
)


class TestInitRuntimeDirs:
    def test_creates_backup_and_log_dirs(self, monkeypatch, tmp_path):
        backup = tmp_path / "fru_backup"
        logs = tmp_path / "logs"
        monkeypatch.setattr(config_mod, "BACKUP_DIR", str(backup))
        monkeypatch.setattr(config_mod, "LOG_DIR", str(logs))
        assert not backup.exists()
        assert not logs.exists()
        init_runtime_dirs()
        assert backup.is_dir()
        assert logs.is_dir()

    def test_idempotent(self, monkeypatch, tmp_path):
        backup = tmp_path / "fru_backup"
        logs = tmp_path / "logs"
        monkeypatch.setattr(config_mod, "BACKUP_DIR", str(backup))
        monkeypatch.setattr(config_mod, "LOG_DIR", str(logs))
        init_runtime_dirs()
        (backup / "existing.bin").write_bytes(b"\x00")
        init_runtime_dirs()
        assert (backup / "existing.bin").exists()


class TestResolveIpmitoolPath:
    def test_prefers_ipmitool_subfolder(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config_mod, "BASE_DIR", str(tmp_path))
        nested = tmp_path / "ipmitool" / "ipmitool.exe"
        nested.parent.mkdir()
        nested.write_text("")
        root_exe = tmp_path / "ipmitool.exe"
        root_exe.write_text("")
        assert resolve_ipmitool_path(refresh=True) == str(nested.resolve())

    def test_falls_back_to_root_layout(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config_mod, "BASE_DIR", str(tmp_path))
        root_exe = tmp_path / "ipmitool.exe"
        root_exe.write_text("")
        assert resolve_ipmitool_path(refresh=True) == str(root_exe.resolve())

    def test_env_override(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config_mod, "BASE_DIR", str(tmp_path))
        custom = tmp_path / "custom" / "ipmitool.exe"
        custom.parent.mkdir()
        custom.write_text("")
        monkeypatch.setenv("FRUTOOL_IPMITOOL", str(custom))
        assert resolve_ipmitool_path(refresh=True) == str(custom.resolve())

    def test_get_ipmitool_dir_matches_parent(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config_mod, "BASE_DIR", str(tmp_path))
        nested = tmp_path / "ipmitool" / "ipmitool.exe"
        nested.parent.mkdir()
        nested.write_text("")
        resolve_ipmitool_path(refresh=True)
        assert get_ipmitool_dir() == str(nested.parent.resolve())

    def test_default_path_when_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config_mod, "BASE_DIR", str(tmp_path))
        monkeypatch.setattr(config_mod.shutil, "which", lambda _name: None)
        resolve_ipmitool_path(refresh=True)
        assert get_ipmitool_path() == str((tmp_path / "ipmitool" / "ipmitool.exe").resolve())

    def test_prefers_base_dir_over_bundled(self, monkeypatch, tmp_path):
        bundled = tmp_path / "bundle"
        bundled_ipmi = bundled / "ipmitool" / "ipmitool.exe"
        bundled_ipmi.parent.mkdir(parents=True)
        bundled_ipmi.write_text("bundled")

        base = tmp_path / "app"
        override = base / "ipmitool" / "ipmitool.exe"
        override.parent.mkdir(parents=True)
        override.write_text("override")

        monkeypatch.setattr(config_mod, "BASE_DIR", str(base))
        monkeypatch.setattr(config_mod.sys, "frozen", True, raising=False)
        monkeypatch.setattr(config_mod.sys, "_MEIPASS", str(bundled), raising=False)
        assert resolve_ipmitool_path(refresh=True) == str(override.resolve())

    def test_falls_back_to_bundled_ipmitool(self, monkeypatch, tmp_path):
        bundled = tmp_path / "bundle"
        bundled_ipmi = bundled / "ipmitool" / "ipmitool.exe"
        bundled_ipmi.parent.mkdir(parents=True)
        bundled_ipmi.write_text("bundled")

        base = tmp_path / "app"
        base.mkdir()
        monkeypatch.setattr(config_mod, "BASE_DIR", str(base))
        monkeypatch.setattr(config_mod.sys, "frozen", True, raising=False)
        monkeypatch.setattr(config_mod.sys, "_MEIPASS", str(bundled), raising=False)
        assert resolve_ipmitool_path(refresh=True) == str(bundled_ipmi.resolve())


class TestResolvePcieEepromTool:
    def test_prefers_ipmitool_dir_script(self, monkeypatch, tmp_path):
        bundled = tmp_path / "bundle"
        bundled.mkdir()
        bundled_ipmi = bundled / "ipmitool"
        bundled_ipmi.mkdir()
        bundled_tool = bundled_ipmi / "PcieEEpromTool.py"
        bundled_tool.write_text("# bundled ipmitool")

        base = tmp_path / "app"
        base.mkdir()
        monkeypatch.setattr(config_mod, "BASE_DIR", str(base))
        monkeypatch.setattr(config_mod.sys, "frozen", True, raising=False)
        monkeypatch.setattr(config_mod.sys, "_MEIPASS", str(bundled), raising=False)
        assert resolve_pcie_eeprom_tool() == str(bundled_tool.resolve())

    def test_prefers_base_dir_ipmitool_override(self, monkeypatch, tmp_path):
        bundled = tmp_path / "bundle" / "ipmitool"
        bundled.mkdir(parents=True)
        bundled_tool = bundled / "PcieEEpromTool.py"
        bundled_tool.write_text("# bundled")

        base = tmp_path / "app"
        base.mkdir()
        override_dir = base / "ipmitool"
        override_dir.mkdir()
        override = override_dir / "PcieEEpromTool.py"
        override.write_text("# override")

        monkeypatch.setattr(config_mod, "BASE_DIR", str(base))
        monkeypatch.setattr(config_mod.sys, "frozen", True, raising=False)
        monkeypatch.setattr(config_mod.sys, "_MEIPASS", str(bundled.parent), raising=False)
        assert resolve_pcie_eeprom_tool() == str(override.resolve())

    def test_legacy_root_override_beside_exe(self, monkeypatch, tmp_path):
        bundled = tmp_path / "bundle"
        bundled.mkdir()

        base = tmp_path / "app"
        base.mkdir()
        override = base / "PcieEEpromTool.py"
        override.write_text("# legacy override")

        monkeypatch.setattr(config_mod, "BASE_DIR", str(base))
        monkeypatch.setattr(config_mod.sys, "frozen", True, raising=False)
        monkeypatch.setattr(config_mod.sys, "_MEIPASS", str(bundled), raising=False)
        assert resolve_pcie_eeprom_tool() == str(override.resolve())

    def test_falls_back_to_bundled_script(self, monkeypatch, tmp_path):
        bundled = tmp_path / "bundle"
        bundled_ipmi = bundled / "ipmitool"
        bundled_ipmi.mkdir(parents=True)
        script = bundled_ipmi / "PcieEEpromTool.py"
        script.write_text("# bundled")

        base = tmp_path / "app"
        base.mkdir()
        monkeypatch.setattr(config_mod, "BASE_DIR", str(base))
        monkeypatch.setattr(config_mod.sys, "frozen", True, raising=False)
        monkeypatch.setattr(config_mod.sys, "_MEIPASS", str(bundled), raising=False)
        assert resolve_pcie_eeprom_tool() == str(script.resolve())


class TestListPcieEepromTools:
    def test_scans_variants_and_prefers_standard_name(self, monkeypatch, tmp_path):
        base = tmp_path / "app"
        ipmi = base / "ipmitool"
        ipmi.mkdir(parents=True)
        (ipmi / "PcieEEpromTool_v2.py").write_text("# v2")
        (ipmi / "PcieEEpromTool.py").write_text("# std")
        (base / "PcieEEpromTool_legacy.py").write_text("# legacy")

        monkeypatch.setattr(config_mod, "BASE_DIR", str(base))
        monkeypatch.setattr(config_mod.sys, "frozen", False, raising=False)
        tools = list_pcie_eeprom_tools()
        names = [t["name"] for t in tools]
        assert names[0] == "PcieEEpromTool.py"
        assert "PcieEEpromTool_v2.py" in names
        assert "PcieEEpromTool_legacy.py" in names
        assert all(" · " in t["label"] for t in tools)

    def test_dedupes_by_abspath(self, monkeypatch, tmp_path):
        base = tmp_path / "app"
        ipmi = base / "ipmitool"
        ipmi.mkdir(parents=True)
        (ipmi / "PcieEEpromTool.py").write_text("# one")
        monkeypatch.setattr(config_mod, "BASE_DIR", str(base))
        monkeypatch.setattr(config_mod.sys, "frozen", False, raising=False)
        tools = list_pcie_eeprom_tools()
        assert len(tools) == 1

    def test_pref_roundtrip(self, monkeypatch, tmp_path):
        logs = tmp_path / "logs"
        logs.mkdir()
        monkeypatch.setattr(config_mod, "LOG_DIR", str(logs))
        monkeypatch.setattr(config_mod, "TOPO_SCRIPT_PREF_JSON", str(logs / "topo_prefs.json"))
        save_topo_script_pref(r"C:\tools\PcieEEpromTool_v2.py")
        assert load_topo_script_pref().endswith("PcieEEpromTool_v2.py")
