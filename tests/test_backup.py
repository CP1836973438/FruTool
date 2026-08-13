"""Tests for FRU backup file helpers."""
from __future__ import annotations

import frutool.domain.backup as backup_mod
from frutool.domain.backup import list_fru_backups_for_sn


class TestListFruBackupsForSn:
    def test_empty_sn(self, monkeypatch, tmp_path):
        monkeypatch.setattr(backup_mod, "BACKUP_DIR", str(tmp_path))
        assert list_fru_backups_for_sn("") == []
        assert list_fru_backups_for_sn("  ") == []

    def test_filters_by_sn_and_excludes_new_original(self, monkeypatch, tmp_path):
        monkeypatch.setattr(backup_mod, "BACKUP_DIR", str(tmp_path))
        (tmp_path / "SN001_20260101.bin").write_bytes(b"\x00")
        (tmp_path / "SN001_NEW_ORIGINAL_20260101.bin").write_bytes(b"\x00")
        (tmp_path / "SN002_20260101.bin").write_bytes(b"\x00")
        (tmp_path / "SN001_20260101.txt").write_text("not bin")
        assert list_fru_backups_for_sn("SN001") == ["SN001_20260101.bin"]

    def test_sorted_results(self, monkeypatch, tmp_path):
        monkeypatch.setattr(backup_mod, "BACKUP_DIR", str(tmp_path))
        (tmp_path / "SN001_20260102.bin").write_bytes(b"\x00")
        (tmp_path / "SN001_20260101.bin").write_bytes(b"\x00")
        assert list_fru_backups_for_sn("SN001") == [
            "SN001_20260101.bin",
            "SN001_20260102.bin",
        ]

    def test_missing_backup_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr(backup_mod, "BACKUP_DIR", str(tmp_path / "nonexistent"))
        assert list_fru_backups_for_sn("SN001") == []
