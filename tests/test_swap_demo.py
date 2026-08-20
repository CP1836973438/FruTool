"""Tests for swap skip-step-1 demo helpers."""
from __future__ import annotations

import os

import frutool.domain.backup as backup_mod
from frutool.demo import DEMO_SKIP_SN
from frutool.demo import swap_demo as swap_demo_mod
from frutool.demo.swap_demo import seed_demo_backup
from frutool.domain.backup import list_fru_backups_for_sn


def test_seed_demo_backup_is_skippable(monkeypatch, tmp_path):
    monkeypatch.setattr(swap_demo_mod, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(swap_demo_mod, "init_runtime_dirs", lambda: None)
    monkeypatch.setattr(backup_mod, "BACKUP_DIR", str(tmp_path))
    path = seed_demo_backup()
    assert os.path.isfile(path)
    assert os.path.basename(path) == f"{DEMO_SKIP_SN}.bin"
    assert list_fru_backups_for_sn(DEMO_SKIP_SN) == [f"{DEMO_SKIP_SN}.bin"]
