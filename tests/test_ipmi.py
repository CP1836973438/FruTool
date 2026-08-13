"""Tests for IPMI integration and FRU parsing."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from frutool.domain import ipmi
from frutool.domain.ipmi import (
    FruFingerprint,
    capture_fru_fingerprint,
    ipmi_base_args,
    mask_ipmi_args,
    parse_board_serial,
    parse_fru_field,
    parse_product_serial,
    probe_bmc_ping,
    probe_fru_list,
    run_ipmi,
    script_python_argv,
)
from tests.conftest import SAMPLE_FRU_OUTPUT


class TestMaskIpmiArgs:
    def test_masks_password(self):
        args = ["-I", "lanplus", "-H", "192.168.1.100", "-U", "admin", "-P", "secret"]
        assert mask_ipmi_args(args)[-1] == "******"

    def test_no_password_unchanged(self):
        args = ["fru", "list", "0"]
        assert mask_ipmi_args(args) == args


class TestIpmiBaseArgs:
    def test_builds_lanplus_args(self):
        assert ipmi_base_args("admin", "pwd", "10.0.0.1") == [
            "-I", "lanplus", "-H", "10.0.0.1", "-U", "admin", "-P", "pwd",
        ]


class TestFruParsing:
    def test_parse_board_serial(self):
        assert parse_board_serial(SAMPLE_FRU_OUTPUT) == "BQWF123456"

    def test_parse_board_serial_missing(self):
        assert parse_board_serial("no serial here") is None

    def test_parse_product_serial(self):
        assert parse_product_serial(SAMPLE_FRU_OUTPUT) == "SN123456789"

    def test_parse_fru_field(self):
        assert parse_fru_field(SAMPLE_FRU_OUTPUT, "Product Name") == "S2600WTTR"

    def test_capture_fru_fingerprint(self):
        fp = capture_fru_fingerprint(SAMPLE_FRU_OUTPUT)
        assert fp is not None
        assert fp.board_serial == "BQWF123456"
        assert fp.product_serial == "SN123456789"
        assert fp.product_name == "S2600WTTR"

    def test_capture_fru_fingerprint_no_board_serial(self):
        assert capture_fru_fingerprint("Product Serial : X") is None


class TestFruFingerprint:
    def test_round_trip_dict(self):
        fp = FruFingerprint("BS1", "PS1", "BoardX")
        restored = FruFingerprint.from_dict(fp.to_dict())
        assert restored == fp


class TestRunIpmi:
    def test_success(self, log_collector):
        entries, log = log_collector
        mock_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("frutool.domain.ipmi.subprocess.run", return_value=mock_result):
            rc, out, err = run_ipmi(["fru", "list", "0"], log)
        assert rc == 0
        assert out == "ok"
        assert any(e[0] == "cmd" for e in entries)

    def test_timeout(self, log_collector):
        entries, log = log_collector
        with patch(
            "frutool.domain.ipmi.subprocess.run",
            side_effect=subprocess.TimeoutExpired("cmd", 30),
        ):
            rc, out, err = run_ipmi(["fru", "list", "0"], log)
        assert rc == -1
        assert err == "timeout"
        assert any(e[0] == "error" for e in entries)

    def test_file_not_found(self, log_collector):
        entries, log = log_collector
        with patch("frutool.domain.ipmi.subprocess.run", side_effect=FileNotFoundError):
            rc, _, err = run_ipmi(["fru", "list", "0"], log)
        assert rc == -1
        assert err == "not found"


class TestProbeFruList:
    def test_missing_credentials(self):
        assert probe_fru_list("", "pwd", "10.0.0.1") == (False, "")

    def test_success(self):
        with patch("frutool.domain.ipmi.run_ipmi", return_value=(0, SAMPLE_FRU_OUTPUT, "")):
            ok, out = probe_fru_list("admin", "pwd", "10.0.0.1")
        assert ok is True
        assert "BQWF123456" in out

    def test_ipmi_failure(self):
        with patch("frutool.domain.ipmi.run_ipmi", return_value=(1, "", "error")):
            ok, out = probe_fru_list("admin", "pwd", "10.0.0.1")
        assert ok is False
        assert out == ""


class TestProbeBmcPing:
    def test_invalid_ip(self):
        assert probe_bmc_ping("") is False
        assert probe_bmc_ping("not-an-ip") is False

    def test_success(self):
        mock_result = MagicMock(returncode=0)
        with patch("frutool.domain.ipmi.subprocess.run", return_value=mock_result):
            assert probe_bmc_ping("192.168.1.1") is True

    def test_ping_failure(self):
        mock_result = MagicMock(returncode=1)
        with patch("frutool.domain.ipmi.subprocess.run", return_value=mock_result):
            assert probe_bmc_ping("192.168.1.1") is False


class TestWaitForBmc:
    def test_succeeds_on_first_probe(self, log_collector, monkeypatch):
        entries, log = log_collector
        monkeypatch.setattr(ipmi, "time", type("T", (), {"time": staticmethod(lambda: 0.0)})())
        with patch("frutool.domain.ipmi.run_ipmi", return_value=(0, SAMPLE_FRU_OUTPUT, "")):
            assert ipmi.wait_for_bmc("admin", "pwd", "10.0.0.1", log, max_wait=10) is True
        assert any(e[0] == "success" for e in entries)

    def test_times_out(self, log_collector, monkeypatch):
        entries, log = log_collector
        clock = {"t": 0.0}

        def fake_time():
            clock["t"] += 6
            return clock["t"]

        monkeypatch.setattr(ipmi, "time", type("T", (), {"time": staticmethod(fake_time), "sleep": staticmethod(lambda _: None)})())
        with patch("frutool.domain.ipmi.run_ipmi", return_value=(1, "", "fail")):
            assert ipmi.wait_for_bmc("admin", "pwd", "10.0.0.1", log, max_wait=5) is False
        assert any(e[0] == "error" for e in entries)


class TestScriptPythonArgv:
    def test_dev_uses_current_interpreter(self, monkeypatch):
        monkeypatch.setattr(ipmi.sys, "frozen", False, raising=False)
        monkeypatch.setattr(ipmi.sys, "executable", r"C:\Python311\python.exe")
        assert script_python_argv() == [r"C:\Python311\python.exe"]

    def test_frozen_prefers_py_launcher(self, monkeypatch):
        monkeypatch.setattr(ipmi.sys, "frozen", True, raising=False)

        def fake_which(name):
            return {
                "py": r"C:\Windows\py.exe",
                "python": r"C:\Users\X\AppData\Local\Microsoft\WindowsApps\python.EXE",
            }.get(name)

        monkeypatch.setattr(ipmi.shutil, "which", fake_which)
        monkeypatch.setattr(ipmi, "_probe_python_argv", lambda argv: argv[:2] == [r"C:\Windows\py.exe", "-3"])
        assert script_python_argv() == [r"C:\Windows\py.exe", "-3"]

    def test_frozen_uses_first_working_candidate(self, monkeypatch, tmp_path):
        monkeypatch.setattr(ipmi.sys, "frozen", True, raising=False)
        real_python = tmp_path / "python.exe"
        real_python.write_text("")

        def fake_which(name):
            if name == "py":
                return None
            if name == "python3":
                return None
            if name == "python":
                return str(real_python)
            return None

        monkeypatch.setattr(ipmi.shutil, "which", fake_which)
        monkeypatch.setattr(ipmi, "_probe_python_argv", lambda argv: argv == [str(real_python)])
        assert script_python_argv() == [str(real_python)]
