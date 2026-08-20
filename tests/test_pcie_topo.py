"""Tests for PCIe topology EEPROM write."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import frutool.domain.pcie_topo as pcie_topo
from frutool.domain.pcie_topo import STAGED_TOPO_SCRIPT_NAME, run_pcie_topology_write, stage_topo_script_for_run


def _prepare_ipmi_dir(tmp_path, monkeypatch):
    ipmi = tmp_path / "ipmitool"
    ipmi.mkdir(exist_ok=True)
    monkeypatch.setattr(pcie_topo, "get_ipmitool_dir", lambda: str(ipmi))
    monkeypatch.setattr(pcie_topo, "BASE_DIR", str(tmp_path))
    return ipmi


class TestStageTopoScript:
    def test_already_in_ipmitool_returns_same(self, log_collector, monkeypatch, tmp_path):
        _, log = log_collector
        ipmi = _prepare_ipmi_dir(tmp_path, monkeypatch)
        tool = ipmi / "PcieEEpromTool.py"
        tool.write_text("# in place")
        staged = stage_topo_script_for_run(str(tool), log)
        assert staged == str(tool.resolve())
        assert not (ipmi / STAGED_TOPO_SCRIPT_NAME).exists()

    def test_copies_outside_script_into_ipmitool(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        ipmi = _prepare_ipmi_dir(tmp_path, monkeypatch)
        src = tmp_path / "PcieEEpromTool_v2.py"
        src.write_text("# outside")
        staged = stage_topo_script_for_run(str(src), log)
        dest = ipmi / STAGED_TOPO_SCRIPT_NAME
        assert staged == str(dest.resolve())
        assert dest.read_text() == "# outside"
        assert any("Loaded topology script" in e[1] for e in entries)


class TestRunPcieTopologyWrite:
    def test_tool_not_found(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        _prepare_ipmi_dir(tmp_path, monkeypatch)
        monkeypatch.setattr(pcie_topo, "resolve_pcie_eeprom_tool", lambda: str(tmp_path / "missing.py"))
        bin_path = tmp_path / "topo.bin"
        bin_path.write_bytes(b"\x00" * 64)
        assert run_pcie_topology_write(str(bin_path), "u", "p", "10.0.0.1", log) is False
        assert any("Topology script" in e[1] or "not found" in e[1] for e in entries)

    def test_bin_not_found(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        ipmi = _prepare_ipmi_dir(tmp_path, monkeypatch)
        tool = ipmi / "PcieEEpromTool.py"
        tool.write_text("# stub")
        monkeypatch.setattr(pcie_topo, "resolve_pcie_eeprom_tool", lambda: str(tool))
        assert run_pcie_topology_write(str(tmp_path / "missing.bin"), "u", "p", "10.0.0.1", log) is False

    def test_bin_too_large(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        ipmi = _prepare_ipmi_dir(tmp_path, monkeypatch)
        tool = ipmi / "PcieEEpromTool.py"
        tool.write_text("# stub")
        monkeypatch.setattr(pcie_topo, "resolve_pcie_eeprom_tool", lambda: str(tool))
        bin_path = tmp_path / "topo.bin"
        bin_path.write_bytes(b"\x00" * 513)
        assert run_pcie_topology_write(str(bin_path), "u", "p", "10.0.0.1", log) is False
        assert any("512 bytes" in e[1] for e in entries)

    def test_success(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        ipmi = _prepare_ipmi_dir(tmp_path, monkeypatch)
        tool = ipmi / "PcieEEpromTool.py"
        tool.write_text("# stub")
        monkeypatch.setattr(pcie_topo, "resolve_pcie_eeprom_tool", lambda: str(tool))
        bin_path = tmp_path / "topo.bin"
        bin_path.write_bytes(b"\x00" * 64)
        mock_result = MagicMock(returncode=0, stdout="done\n", stderr="")
        with patch("frutool.domain.pcie_topo.script_python_argv", return_value=["python"]):
            with patch("frutool.domain.pcie_topo.subprocess.run", return_value=mock_result) as run_mock:
                assert run_pcie_topology_write(str(bin_path), "u", "p", "10.0.0.1", log) is True
                assert run_mock.call_args.kwargs.get("cwd") == str(ipmi)
                assert str(tool) in run_mock.call_args.args[0]
        assert any(e[0] == "success" for e in entries)

    def test_stages_outside_script_then_runs(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        ipmi = _prepare_ipmi_dir(tmp_path, monkeypatch)
        default_tool = ipmi / "PcieEEpromTool.py"
        default_tool.write_text("# default")
        other = tmp_path / "elsewhere" / "PcieEEpromTool_v2.py"
        other.parent.mkdir()
        other.write_text("# other")
        monkeypatch.setattr(pcie_topo, "resolve_pcie_eeprom_tool", lambda: str(default_tool))
        bin_path = tmp_path / "topo.bin"
        bin_path.write_bytes(b"\x00" * 64)
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        staged = ipmi / STAGED_TOPO_SCRIPT_NAME
        with patch("frutool.domain.pcie_topo.script_python_argv", return_value=["python"]):
            with patch("frutool.domain.pcie_topo.subprocess.run", return_value=mock_result) as run_mock:
                assert run_pcie_topology_write(
                    str(bin_path), "u", "p", "10.0.0.1", log, script_path=str(other)
                ) is True
                cmd = run_mock.call_args.args[0]
                assert str(staged) in cmd
                assert str(other) not in cmd
                assert run_mock.call_args.kwargs["cwd"] == str(ipmi)
        assert staged.read_text() == "# other"
        assert any("Loaded topology script" in e[1] for e in entries)

    def test_timeout(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        ipmi = _prepare_ipmi_dir(tmp_path, monkeypatch)
        tool = ipmi / "PcieEEpromTool.py"
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
                assert any("timed out" in e[1] for e in entries)
