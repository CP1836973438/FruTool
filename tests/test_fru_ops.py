"""Tests for FRU export/clone workflow."""
from __future__ import annotations

from unittest.mock import patch

import frutool.domain.fru_ops as fru_ops
from frutool.domain.fru_ops import run_step1_export, run_step2_clone
from tests.conftest import SAMPLE_FRU_OUTPUT, make_run_ipmi_mock


class TestRunStep1Export:
    def test_success_with_skip_wait(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))
        fake_ipmi = make_run_ipmi_mock()
        with patch("frutool.domain.fru_ops.run_ipmi", fake_ipmi):
            with patch("frutool.domain.fru_ops.probe_fru_list", return_value=(True, SAMPLE_FRU_OUTPUT)):
                result = run_step1_export(
                    "SN001", "admin", "pwd", "10.0.0.1", log, skip_wait=True,
                )
        assert result["ok"] is True
        assert result["bmc_online"] is True
        assert "bin_path" in result

    def test_bmc_not_ready_with_skip_wait(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))
        with patch("frutool.domain.fru_ops.probe_fru_list", return_value=(False, "")):
            with patch("frutool.domain.fru_ops.time.sleep", lambda _: None):
                result = run_step1_export(
                    "SN001", "admin", "pwd", "10.0.0.1", log, skip_wait=True,
                )
        assert result["ok"] is False
        assert result["bmc_online"] is False

    def test_wait_for_bmc_timeout(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))
        with patch("frutool.domain.fru_ops.wait_for_bmc", return_value=False):
            result = run_step1_export("SN001", "admin", "pwd", "10.0.0.1", log)
        assert result["ok"] is False
        assert result["title"] == "超时"

    def test_export_read_failure(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))

        def fail_read(args_list, log_cb=None, timeout=30):
            return 1, "", "read failed"

        with patch("frutool.domain.fru_ops.wait_for_bmc", return_value=True):
            with patch("frutool.domain.fru_ops.run_ipmi", fail_read):
                result = run_step1_export("SN001", "admin", "pwd", "10.0.0.1", log)
        assert result["ok"] is False
        assert result["title"] == "失败"


class TestRunStep2Clone:
    def test_success(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))
        old_bin = tmp_path / "old.bin"
        old_bin.write_bytes(b"\x01" * 128)
        fake_ipmi = make_run_ipmi_mock()
        with patch("frutool.domain.fru_ops.wait_for_bmc", return_value=True):
            with patch("frutool.domain.fru_ops.run_ipmi", fake_ipmi):
                result = run_step2_clone(
                    "SN001", "admin", "pwd", "10.0.0.1", str(old_bin), log,
                )
        assert result["ok"] is True
        assert result["serial"] == "BQWF123456"

    def test_fru_list_failure(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))
        old_bin = tmp_path / "old.bin"
        old_bin.write_bytes(b"\x01" * 128)

        def fail_list(args_list, log_cb=None, timeout=30):
            if "fru list" in " ".join(args_list):
                return 1, "", "fail"
            return 0, "", ""

        with patch("frutool.domain.fru_ops.wait_for_bmc", return_value=True):
            with patch("frutool.domain.fru_ops.run_ipmi", fail_list):
                result = run_step2_clone(
                    "SN001", "admin", "pwd", "10.0.0.1", str(old_bin), log,
                )
        assert result["ok"] is False
        assert result["title"] == "读取失败"

    def test_write_failure(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))
        old_bin = tmp_path / "old.bin"
        old_bin.write_bytes(b"\x01" * 128)

        def fail_on_write(args_list, log_cb=None, timeout=30):
            cmd = " ".join(args_list)
            if "fru write" in cmd:
                return 1, "", "write failed"
            if "fru list" in cmd:
                return 0, SAMPLE_FRU_OUTPUT, ""
            if "fru read" in cmd:
                path = args_list[-1]
                with open(path, "wb") as fh:
                    fh.write(b"\x00" * 64)
                return 0, "", ""
            return 0, "", ""

        with patch("frutool.domain.fru_ops.wait_for_bmc", return_value=True):
            with patch("frutool.domain.fru_ops.run_ipmi", fail_on_write):
                result = run_step2_clone(
                    "SN001", "admin", "pwd", "10.0.0.1", str(old_bin), log,
                )
        assert result["ok"] is False
        assert result["title"] == "写入失败"

    def test_edit_failure(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))
        old_bin = tmp_path / "old.bin"
        old_bin.write_bytes(b"\x01" * 128)

        def fail_on_edit(args_list, log_cb=None, timeout=30):
            cmd = " ".join(args_list)
            if "fru edit" in cmd:
                return 1, "", "edit failed"
            if "fru write" in cmd:
                return 0, "", ""
            if "fru list" in cmd:
                return 0, SAMPLE_FRU_OUTPUT, ""
            if "fru read" in cmd:
                path = args_list[-1]
                with open(path, "wb") as fh:
                    fh.write(b"\x00" * 64)
                return 0, "", ""
            return 0, "", ""

        with patch("frutool.domain.fru_ops.wait_for_bmc", return_value=True):
            with patch("frutool.domain.fru_ops.run_ipmi", fail_on_edit):
                result = run_step2_clone(
                    "SN001", "admin", "pwd", "10.0.0.1", str(old_bin), log,
                )
        assert result["ok"] is False
        assert result["title"] == "还原失败"
