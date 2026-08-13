"""Tests for PCIe topology EEPROM write."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import frutool.domain.pcie_topo as pcie_topo
from frutool.domain.pcie_topo import run_pcie_topology_write


class TestRunPcieTopologyWrite:
    def test_tool_not_found(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.setattr(pcie_topo, "resolve_pcie_eeprom_tool", lambda: str(tmp_path / "missing.py"))
        bin_path = tmp_path / "topo.bin"
        bin_path.write_bytes(b"\x00" * 64)
        assert run_pcie_topology_write(str(bin_path), "u", "p", "10.0.0.1", log) is False
        assert any("PcieEEpromTool" in e[1] for e in entries)

    def test_bin_not_found(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        tool = tmp_path / "PcieEEpromTool.py"
        tool.write_text("# stub")
        monkeypatch.setattr(pcie_topo, "resolve_pcie_eeprom_tool", lambda: str(tool))
        assert run_pcie_topology_write(str(tmp_path / "missing.bin"), "u", "p", "10.0.0.1", log) is False

    def test_bin_too_large(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        tool = tmp_path / "PcieEEpromTool.py"
        tool.write_text("# stub")
        monkeypatch.setattr(pcie_topo, "resolve_pcie_eeprom_tool", lambda: str(tool))
        bin_path = tmp_path / "topo.bin"
        bin_path.write_bytes(b"\x00" * 513)
        assert run_pcie_topology_write(str(bin_path), "u", "p", "10.0.0.1", log) is False
        assert any("512 bytes" in e[1] for e in entries)

    def test_success(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        tool = tmp_path / "PcieEEpromTool.py"
        tool.write_text("# stub")
        monkeypatch.setattr(pcie_topo, "resolve_pcie_eeprom_tool", lambda: str(tool))
        monkeypatch.setattr(pcie_topo, "BASE_DIR", str(tmp_path))
        bin_path = tmp_path / "topo.bin"
        bin_path.write_bytes(b"\x00" * 64)
        mock_result = MagicMock(returncode=0, stdout="done\n", stderr="")
        with patch("frutool.domain.pcie_topo.script_python_argv", return_value=["python"]):
            with patch("frutool.domain.pcie_topo.subprocess.run", return_value=mock_result) as run_mock:
                assert run_pcie_topology_write(str(bin_path), "u", "p", "10.0.0.1", log) is True
                assert run_mock.call_args.kwargs.get("cwd") is not None
        assert any(e[0] == "success" for e in entries)

    def test_timeout(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        tool = tmp_path / "PcieEEpromTool.py"
        tool.write_text("# stub")
        monkeypatch.setattr(pcie_topo, "resolve_pcie_eeprom_tool", lambda: str(tool))
        bin_path = tmp_path / "topo.bin"
        bin_path.write_bytes(b"\x00" * 64)
        with patch("frutool.domain.pcie_topo.script_python_argv", return_value=["python"]):
            with patch(
                "frutool.domain.pcie_topo.subprocess.run",
                side_effect=subprocess.TimeoutExpired("cmd", 120),
            ):
                assert run_pcie_topology_write(str(bin_path), "u", "p", "10.0.0.1", log) is False
