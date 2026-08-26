"""Tests for FRU export/clone workflow."""
from __future__ import annotations

from unittest.mock import patch

import pytest

import frutool.domain.fru_ops as fru_ops
from frutool.domain.fru_ops import run_step1_export, run_step2_clone, should_restore_new_board_pn
from tests.conftest import SAMPLE_FRU_OUTPUT, make_run_ipmi_mock


@pytest.fixture(autouse=True)
def _clear_demo_env(monkeypatch):
    monkeypatch.delenv("FRUTOOL_DEMO_SWAP", raising=False)
    monkeypatch.delenv("FRUTOOL_DEMO_ALL", raising=False)


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
        assert result["pn_restored"] is False

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


NEW_BOARD_PN_FRU = """
 Board Serial         : NEWBOARD99
 Board Part Number    : YZMB-NEW-PN
"""


def _clone_ipmi_mock(*, list_outputs: list[str], fail_edit_index: str | None = None):
    lists = list(list_outputs)
    edits: list[str] = []

    def fake(args_list, log_cb=None, timeout=30):
        cmd = " ".join(args_list)
        if "fru list" in cmd:
            out = lists.pop(0) if lists else list_outputs[-1]
            return 0, out, ""
        if "fru read" in cmd:
            path = args_list[-1]
            with open(path, "wb") as fh:
                fh.write(b"\x00" * 64)
            return 0, "", ""
        if "fru write" in cmd:
            return 0, "", ""
        if "fru print" in cmd:
            return 0, SAMPLE_FRU_OUTPUT, ""
        if "fru edit" in cmd:
            edits.append(cmd)
            if fail_edit_index and f"field b {fail_edit_index}" in cmd:
                return 1, "", "edit failed"
            return 0, "", ""
        return 0, "", ""

    fake.edits = edits
    return fake


class TestRestoreBoardPn:
    def test_same_pn_skips_part_number_edit(self):
        assert should_restore_new_board_pn("YZMB-10F", "yzmb-10f") is False
        assert should_restore_new_board_pn("", "YZMB-10F") is False

    def test_different_pn_restores(self):
        assert should_restore_new_board_pn("YZMB-NEW", "YZMB-OLD") is True

    def test_clone_same_pn_only_edits_serial(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.delenv("FRUTOOL_DEMO_SWAP", raising=False)
        monkeypatch.delenv("FRUTOOL_DEMO_ALL", raising=False)
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))
        old_bin = tmp_path / "old.bin"
        old_bin.write_bytes(b"\x01" * 128)
        fake = _clone_ipmi_mock(list_outputs=[SAMPLE_FRU_OUTPUT, SAMPLE_FRU_OUTPUT])
        with patch("frutool.domain.fru_ops.wait_for_bmc", return_value=True):
            with patch("frutool.domain.fru_ops.run_ipmi", fake):
                result = run_step2_clone("SN001", "admin", "pwd", "10.0.0.1", str(old_bin), log)
        assert result["ok"] is True
        assert result["pn_restored"] is False
        assert any("field b 2" in cmd for cmd in fake.edits)
        assert not any("field b 3" in cmd for cmd in fake.edits)

    def test_clone_different_pn_edits_serial_and_pn(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.delenv("FRUTOOL_DEMO_SWAP", raising=False)
        monkeypatch.delenv("FRUTOOL_DEMO_ALL", raising=False)
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))
        old_bin = tmp_path / "old.bin"
        old_bin.write_bytes(b"\x01" * 128)
        fake = _clone_ipmi_mock(list_outputs=[NEW_BOARD_PN_FRU, SAMPLE_FRU_OUTPUT])
        with patch("frutool.domain.fru_ops.wait_for_bmc", return_value=True):
            with patch("frutool.domain.fru_ops.run_ipmi", fake):
                result = run_step2_clone("SN001", "admin", "pwd", "10.0.0.1", str(old_bin), log)
        assert result["ok"] is True
        assert result["serial"] == "NEWBOARD99"
        assert result["part_number"] == "YZMB-NEW-PN"
        assert result["pn_restored"] is True
        assert any("field b 2" in cmd and "NEWBOARD99" in cmd for cmd in fake.edits)
        assert any("field b 3" in cmd and "YZMB-NEW-PN" in cmd for cmd in fake.edits)

    def test_pn_edit_failure(self, log_collector, monkeypatch, tmp_path):
        entries, log = log_collector
        monkeypatch.delenv("FRUTOOL_DEMO_SWAP", raising=False)
        monkeypatch.delenv("FRUTOOL_DEMO_ALL", raising=False)
        monkeypatch.setattr(fru_ops, "BACKUP_DIR", str(tmp_path))
        old_bin = tmp_path / "old.bin"
        old_bin.write_bytes(b"\x01" * 128)
        fake = _clone_ipmi_mock(
            list_outputs=[NEW_BOARD_PN_FRU, SAMPLE_FRU_OUTPUT],
            fail_edit_index="3",
        )
        with patch("frutool.domain.fru_ops.wait_for_bmc", return_value=True):
            with patch("frutool.domain.fru_ops.run_ipmi", fake):
                result = run_step2_clone("SN001", "admin", "pwd", "10.0.0.1", str(old_bin), log)
        assert result["ok"] is False
        assert result["title"] == "还原失败"
        assert "Board Part Number" in result["message"]

