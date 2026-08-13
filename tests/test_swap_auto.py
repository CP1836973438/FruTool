"""Tests for auto swap domain logic."""
from __future__ import annotations

from unittest.mock import patch

from frutool.domain.swap.auto import (
    apply_poll_result,
    auto_phase_running,
    build_session_restore_plan,
    build_sn_confirm_dialog,
    evaluate_wait_new_tick,
    restore_prompt_message,
    run_capture_fingerprint_job,
    run_sn_detect_job,
    run_swap_poll_job,
    validate_auto_export,
)
from frutool.domain.ipmi import FruFingerprint
from tests.conftest import NEW_BOARD_FRU_OUTPUT, SAMPLE_FRU_OUTPUT

class TestValidateAutoExport:
    def test_rejects_empty_sn(self, tmp_path):
        ipmi = tmp_path / "ipmitool.exe"
        ipmi.write_text("")
        err = validate_auto_export("", "user", "pwd", str(ipmi))
        assert err == ("导出失败", "服务器 SN 为空，无法导出", "critical")

    def test_rejects_missing_credentials(self, tmp_path):
        ipmi = tmp_path / "ipmitool.exe"
        ipmi.write_text("")
        err = validate_auto_export("SN123", "", "pwd", str(ipmi))
        assert err == ("导出失败", "旧板凭据未配置", "critical")

    def test_rejects_missing_ipmitool(self, monkeypatch):
        monkeypatch.setattr("frutool.config.resolve_ipmitool_path", lambda refresh=False: None)
        err = validate_auto_export("SN123", "user", "pwd", "/nonexistent/ipmitool.exe")
        assert err[0] == "导出失败"
        assert "ipmitool" in err[1]

    def test_accepts_valid_input(self, monkeypatch, tmp_path):
        ipmi = tmp_path / "ipmitool.exe"
        ipmi.write_text("")
        monkeypatch.setattr("frutool.config.resolve_ipmitool_path", lambda refresh=False: str(ipmi))
        assert validate_auto_export("SN123", "user", "pwd", str(ipmi)) is None


class TestAutoPhaseRunning:
    def test_idle_and_done_are_not_running(self):
        assert auto_phase_running("idle") is False
        assert auto_phase_running("done") is False

    def test_active_phases_are_running(self):
        assert auto_phase_running("wait_swap") is True
        assert auto_phase_running("sn_confirm") is True


class TestApplyPollResult:
    def test_wait_swap_offline_streak_triggers_wait_new(self):
        transition = apply_poll_result(
            current_phase="wait_swap",
            result={"phase": "wait_swap", "streak": 1},
            offline_streak=2,
            offline_streak_threshold=3,
            now=1000.0,
        )
        assert transition is not None
        assert transition.offline_streak == 0  # reset after threshold reached
        assert transition.next_phase == "wait_new"
        assert transition.wait_new_started_at == 1000.0

    def test_wait_new_clone_detected(self):
        transition = apply_poll_result(
            current_phase="wait_new",
            result={"phase": "wait_new", "action": "clone"},
            offline_streak=0,
            offline_streak_threshold=3,
            now=1000.0,
        )
        assert transition is not None
        assert transition.start_clone is True
        assert transition.stop_poll is True

    def test_invalid_result_returns_none(self):
        assert apply_poll_result(
            current_phase="wait_swap",
            result="not a dict",
            offline_streak=0,
            offline_streak_threshold=3,
            now=0.0,
        ) is None

    def test_wait_swap_resets_streak_when_online(self):
        transition = apply_poll_result(
            current_phase="wait_swap",
            result={"phase": "wait_swap", "streak": 0},
            offline_streak=2,
            offline_streak_threshold=3,
            now=1000.0,
        )
        assert transition is not None
        assert transition.offline_streak == 0
        assert transition.next_phase is None

    def test_mismatched_phase_returns_none(self):
        assert apply_poll_result(
            current_phase="wait_new",
            result={"phase": "wait_swap", "streak": 1},
            offline_streak=0,
            offline_streak_threshold=3,
            now=0.0,
        ) is None


class TestEvaluateWaitNewTick:
    def test_timeout(self):
        tick = evaluate_wait_new_tick(
            wait_new_started_at=0.0,
            last_heartbeat_at=None,
            now=7200.0,
            timeout_s=7200.0,
            heartbeat_s=300.0,
            status_text_fn=lambda: "waiting",
        )
        assert tick.timed_out is True

    def test_heartbeat_when_interval_elapsed(self):
        tick = evaluate_wait_new_tick(
            wait_new_started_at=0.0,
            last_heartbeat_at=0.0,
            now=400.0,
            timeout_s=7200.0,
            heartbeat_s=300.0,
            status_text_fn=lambda: "still waiting",
        )
        assert tick.timed_out is False
        assert tick.heartbeat_message == "still waiting"
        assert tick.refresh_status is True

    def test_refresh_without_heartbeat(self):
        tick = evaluate_wait_new_tick(
            wait_new_started_at=0.0,
            last_heartbeat_at=350.0,
            now=400.0,
            timeout_s=7200.0,
            heartbeat_s=300.0,
            status_text_fn=lambda: "unused",
        )
        assert tick.heartbeat_message is None
        assert tick.refresh_status is True


class TestBuildSnConfirmDialog:
    def test_builds_dialog_payload(self):
        fp = FruFingerprint(
            product_serial="PS123",
            board_serial="BS456",
            product_name="TestBoard",
        )
        payload = build_sn_confirm_dialog(fp, dialog_id="dlg-1", timeout_s=60)
        assert payload["type"] == "sn_confirm"
        assert payload["productSerial"] == "PS123"
        assert payload["countdown"] == 60

    def test_no_countdown_without_product_serial(self):
        fp = FruFingerprint(product_serial="", board_serial="BS456", product_name="X")
        payload = build_sn_confirm_dialog(fp, dialog_id="dlg-2", timeout_s=60)
        assert payload["countdown"] == 0


class TestRunSnDetectJob:
    def test_success(self, log_collector):
        _, log = log_collector
        with patch("frutool.domain.swap.auto.probe_fru_list", return_value=(True, SAMPLE_FRU_OUTPUT)):
            result = run_sn_detect_job("admin", "pwd", "10.0.0.1", log)
        assert result["ok"] is True
        assert result["fingerprint"].board_serial == "BQWF123456"

    def test_probe_failure(self, log_collector):
        _, log = log_collector
        with patch("frutool.domain.swap.auto.probe_fru_list", return_value=(False, "")):
            assert run_sn_detect_job("admin", "pwd", "10.0.0.1", log) == {"ok": False}

    def test_no_fingerprint_in_output(self, log_collector):
        _, log = log_collector
        with patch("frutool.domain.swap.auto.probe_fru_list", return_value=(True, "no serial")):
            assert run_sn_detect_job("admin", "pwd", "10.0.0.1", log) == {"ok": False}


class TestRunSwapPollJob:
    def test_wait_swap_still_online(self, log_collector):
        _, log = log_collector
        cached = FruFingerprint("BQWF123456", "SN123456789")
        with patch("frutool.domain.swap.auto.probe_fru_list", return_value=(True, SAMPLE_FRU_OUTPUT)):
            result = run_swap_poll_job(
                "wait_swap", "old_u", "old_p", "new_u", "new_p", "10.0.0.1", cached, log,
            )
        assert result == {"phase": "wait_swap", "streak": 0}

    def test_wait_swap_offline(self, log_collector):
        _, log = log_collector
        cached = FruFingerprint("BQWF123456", "SN123456789")
        with patch("frutool.domain.swap.auto.probe_fru_list", return_value=(False, "")):
            result = run_swap_poll_job(
                "wait_swap", "old_u", "old_p", "new_u", "new_p", "10.0.0.1", cached, log,
            )
        assert result == {"phase": "wait_swap", "streak": 1}

    def test_wait_new_still_waiting(self, log_collector):
        _, log = log_collector
        cached = FruFingerprint("BQWF123456", "SN123456789")
        with patch("frutool.domain.swap.auto.probe_fru_list", return_value=(True, SAMPLE_FRU_OUTPUT)):
            result = run_swap_poll_job(
                "wait_new", "old_u", "old_p", "new_u", "new_p", "10.0.0.1", cached, log,
            )
        assert result == {"phase": "wait_new", "action": "wait"}

    def test_wait_new_detects_clone(self, log_collector):
        _, log = log_collector
        cached = FruFingerprint("BQWF123456", "SN123456789")
        with patch("frutool.domain.swap.auto.probe_fru_list", return_value=(True, NEW_BOARD_FRU_OUTPUT)):
            result = run_swap_poll_job(
                "wait_new", "old_u", "old_p", "new_u", "new_p", "10.0.0.1", cached, log,
            )
        assert result == {"phase": "wait_new", "action": "clone"}


class TestRunCaptureFingerprintJob:
    def test_returns_fingerprint(self, log_collector):
        _, log = log_collector
        with patch("frutool.domain.swap.auto.probe_fru_list", return_value=(True, SAMPLE_FRU_OUTPUT)):
            fp = run_capture_fingerprint_job("admin", "pwd", "10.0.0.1", log)
        assert fp is not None
        assert fp.board_serial == "BQWF123456"

    def test_probe_failure_returns_none(self, log_collector):
        _, log = log_collector
        with patch("frutool.domain.swap.auto.probe_fru_list", return_value=(False, "")):
            assert run_capture_fingerprint_job("admin", "pwd", "10.0.0.1", log) is None


class TestBuildSessionRestorePlan:
    def test_sn_confirm_restore(self, tmp_path):
        plan = build_session_restore_plan(
            {
                "swap_auto_phase": "sn_confirm",
                "sn": "SN001",
                "old_fingerprint": {"board_serial": "B1", "product_serial": "P1"},
            },
            now=1000.0,
            timeout_s=7200.0,
            backup_dir=str(tmp_path),
        )
        assert plan.restore_phase == "sn_confirm"
        assert plan.show_sn_confirm is True
        assert plan.start_poll is False

    def test_wait_new_timeout(self, tmp_path):
        from frutool.domain.swap.session import parse_wait_new_started_at

        started_at = parse_wait_new_started_at("2020-01-01T00:00:00")
        assert started_at is not None
        plan = build_session_restore_plan(
            {
                "swap_auto_phase": "wait_new",
                "sn": "SN001",
                "wait_new_started_at": "2020-01-01T00:00:00",
            },
            now=started_at + 7201,
            timeout_s=7200.0,
            backup_dir=str(tmp_path),
        )
        assert plan.timed_out is True
        assert plan.clear_session is True


class TestRestorePromptMessage:
    def test_includes_sn_and_label(self):
        msg = restore_prompt_message("SN001", "等待换板")
        assert "SN001" in msg
        assert "等待换板" in msg