"""Tests for swap session persistence."""
from __future__ import annotations

import json

from frutool.domain.swap.session import (
    build_session_payload,
    clear_session,
    format_wait_new_countdown,
    is_resumable,
    load_session,
    normalize_restore_phase,
    parse_wait_new_started_at,
    phase_label,
    save_session,
    should_discard_loaded,
    wait_new_remaining_seconds,
)


class TestResumable:
    def test_auto_resumable_phases(self):
        assert is_resumable("auto", "wait_swap") is True
        assert is_resumable("auto", "idle") is False
        assert is_resumable("manual", "wait_swap") is False


class TestShouldDiscardLoaded:
    def test_discard_when_step2_done(self):
        assert should_discard_loaded({"step2_done": True, "swap_mode": "auto"}) is True

    def test_discard_when_not_auto(self):
        assert should_discard_loaded({"swap_mode": "manual", "swap_auto_phase": "wait_swap"}) is True

    def test_keep_active_auto_session(self):
        assert should_discard_loaded({"swap_mode": "auto", "swap_auto_phase": "wait_swap"}) is False


class TestBuildSessionPayload:
    def test_builds_versioned_payload(self):
        payload = build_session_payload(
            auto_phase="wait_swap",
            sn=" SN1 ",
            step1_done=True,
            step2_done=False,
            old_fingerprint={"board_serial": "B1"},
            wait_new_started_at=1_700_000_000.0,
            last_export_bin="SN1_20260101.bin",
            new_board_fru_backup_path=None,
        )
        assert payload["version"] == 1
        assert payload["sn"] == "SN1"
        assert payload["swap_auto_phase"] == "wait_swap"
        assert payload["wait_new_started_at"] is not None


class TestNormalizeRestorePhase:
    def test_exporting_with_valid_bin(self, tmp_path):
        (tmp_path / "backup.bin").write_text("")
        phase, clear = normalize_restore_phase("exporting", "backup.bin", str(tmp_path))
        assert phase == "wait_swap"
        assert clear is False

    def test_exporting_without_bin_clears(self, tmp_path):
        phase, clear = normalize_restore_phase("exporting", "missing.bin", str(tmp_path))
        assert phase == "idle"
        assert clear is True

    def test_non_mid_state_unchanged(self, tmp_path):
        phase, clear = normalize_restore_phase("wait_new", None, str(tmp_path))
        assert phase == "wait_new"
        assert clear is False


class TestWaitNewTiming:
    def test_parse_iso_timestamp(self):
        ts = parse_wait_new_started_at("2026-06-23T12:00:00")
        assert ts is not None

    def test_parse_invalid_returns_none(self):
        assert parse_wait_new_started_at("not-a-date") is None

    def test_remaining_seconds(self):
        assert wait_new_remaining_seconds(100.0, 150.0, 7200.0) == 7150.0

    def test_format_countdown(self):
        assert format_wait_new_countdown(3661) == "等待新板上线，剩余 1:01:01"


class TestPhaseLabel:
    def test_known_phase(self):
        assert phase_label("wait_swap") == "等待换板"

    def test_unknown_phase_passthrough(self):
        assert phase_label("custom") == "custom"


class TestSessionFileIO:
    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "session.json")
        data = {"swap_mode": "auto", "sn": "X1"}
        assert save_session(path, data) is None
        loaded, err = load_session(path)
        assert err is None
        assert loaded == data

    def test_load_missing_file(self, tmp_path):
        loaded, err = load_session(str(tmp_path / "missing.json"))
        assert loaded is None
        assert err is None

    def test_load_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        loaded, err = load_session(str(path))
        assert loaded is None
        assert err is not None

    def test_clear_session(self, tmp_path):
        path = tmp_path / "session.json"
        path.write_text("{}", encoding="utf-8")
        clear_session(str(path))
        assert not path.exists()
