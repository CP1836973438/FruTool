"""Auto swap workflow — SN detect, export, poll, clone jobs."""
from __future__ import annotations

import os
import time
import uuid
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer

from frutool.config import (
    BACKUP_DIR,
    LogCallback,
    SWAP_NEW_BOARD_TIMEOUT_S,
    SWAP_OFFLINE_STREAK,
    SWAP_POLL_JOB_TIMEOUT_S,
    SWAP_SN_CONFIRM_TIMEOUT_S,
    SWAP_WAIT_NEW_HEARTBEAT_S,
    get_ipmitool_path,
)
from frutool.domain.ipmi import FruFingerprint
from frutool.domain.swap.auto import (
    apply_poll_result,
    build_sn_confirm_dialog,
    evaluate_wait_new_tick,
    run_capture_fingerprint_job,
    run_sn_detect_job,
    run_swap_poll_job,
    validate_auto_export,
)
from frutool.presentation.services import list_step1_backups, plan_step1_bin_path, run_step1_job, run_step2_job

if TYPE_CHECKING:
    from frutool.presentation.controller.auto_swap_session import AutoSwapSessionController


class AutoSwapWorkflow:
    """Runs background jobs for the automatic swap pipeline."""

    def __init__(self, session: AutoSwapSessionController) -> None:
        self._session = session

    @property
    def _host(self):
        return self._session._host

    @property
    def _conn(self):
        return self._session._conn

    @property
    def _progress(self):
        return self._session._progress

    @property
    def _swap_auto(self):
        return self._session._swap_auto

    def _old_credentials(self) -> tuple[str, str]:
        return self._conn.credentials(False)

    def _new_credentials(self) -> tuple[str, str]:
        return self._conn.credentials(True)

    def _log(self, level: str, message: str) -> None:
        self._session.auto_log(level, message)

    def _release_poll(self) -> None:
        self._swap_auto.state.poll_in_flight = False
        self._swap_auto.state.poll_started_at = None

    def _poll_stuck(self) -> bool:
        if not self._swap_auto.state.poll_in_flight:
            return False
        started = self._swap_auto.state.poll_started_at
        if started is None or time.time() - started <= SWAP_POLL_JOB_TIMEOUT_S:
            return True
        self._log("warning", "换板轮询超时，已强制恢复")
        self._release_poll()
        return False

    def start_sn_detect(self) -> None:
        if self._swap_auto.state.mode != "auto" or self._swap_auto.state.phase not in ("idle",):
            return
        if self._host.busy or self._swap_auto.state.poll_in_flight:
            return
        user, pwd = self._old_credentials()
        if not user or not pwd:
            self._log("warning", "旧板凭据未配置，无法自动检测")
            return
        self._session.set_phase("sn_detect")
        bmc_ip = self._conn.bmc_ip

        def job(log: LogCallback):
            return run_sn_detect_job(user, pwd, bmc_ip, log)

        def done(result: object):
            if self._swap_auto.state.mode != "auto" or self._swap_auto.state.phase != "sn_detect":
                return
            if not isinstance(result, dict) or not result.get("ok"):
                self._log("warning", "旧板 FRU 读取失败，将在 BMC 保持在线时重试")
                self._session.set_phase("idle")
                return
            fp = result["fingerprint"]
            if fp.product_serial:
                self._progress.set_old_board_sn(fp.product_serial)
            self._swap_auto.state.old_fingerprint = fp
            self._log(
                "success",
                f"旧板 FRU: Product Serial={fp.product_serial or '—'}, Board Serial={fp.board_serial}",
            )
            self._session.set_phase("sn_confirm")
            self.show_sn_confirm(fp)

        self._host.run_worker(job, done, log_tab="fru")

    def show_sn_confirm(self, fingerprint: FruFingerprint) -> None:
        self._swap_auto.state.pending_sn_confirm_fp = fingerprint
        payload = build_sn_confirm_dialog(
            fingerprint,
            dialog_id=str(uuid.uuid4()),
            timeout_s=SWAP_SN_CONFIRM_TIMEOUT_S,
        )
        self._host.request_dialog(payload)

    def start_export(self) -> None:
        sn = self._progress.old_board_sn.strip()
        user, pwd = self._old_credentials()
        err = validate_auto_export(sn, user, pwd, get_ipmitool_path())
        if err:
            _title, message, _kind = err
            self._log("error", message)
            self._session.reset(switch_manual=True)
            return

        self._progress.set_step1_done(False)
        self._progress.set_step2_done(False)
        self._progress.set_new_board_fru_backup_path(None)
        self._progress.emit_progress_step()
        self._host.set_busy(True)
        self._session.set_phase("exporting")
        bmc_ip = self._conn.bmc_ip
        bin_path = plan_step1_bin_path(sn)

        def job(log: LogCallback):
            return run_step1_job(sn, user, pwd, bmc_ip, bin_path, log, skip_wait=True)

        self._host.run_worker(job, self._on_export_done, log_tab="fru")

    def _on_export_done(self, result: object) -> None:
        self._host.set_busy(False)
        self._conn.apply_bmc_state_from_result(result)
        if isinstance(result, dict) and result.get("ok"):
            self._progress.set_step1_done(True)
            self._progress.set_last_synced_sn(self._progress.old_board_sn.strip())
            bin_path = result.get("bin_path", "")
            if bin_path:
                self._swap_auto.state.last_export_bin = os.path.basename(bin_path)
            if not self._swap_auto.state.old_fingerprint:
                self.ensure_fingerprint_async()
            self._swap_auto.state.offline_streak = 0
            self._log("success", "FRU 备份完成，等待换板（旧板离线）")
            self._session.set_phase("wait_swap")
            self._session.start_poll_timer()
            self._progress.refresh_capabilities()
        else:
            self._session.set_phase("idle")
            data = result if isinstance(result, dict) else {}
            self._host.request_critical(data.get("title", "失败"), data.get("message", "自动导出失败。"))

    def ensure_fingerprint_async(self) -> None:
        user, pwd = self._old_credentials()
        bmc_ip = self._conn.bmc_ip

        def job(_log: LogCallback):
            return run_capture_fingerprint_job(user, pwd, bmc_ip, _log)

        def done(result: object):
            if isinstance(result, FruFingerprint):
                self._swap_auto.state.old_fingerprint = result
                self._session.persist_session()

        self._host.run_worker(job, done)

    def on_poll_tick(self) -> None:
        if self._swap_auto.state.mode != "auto" or self._swap_auto.state.phase not in ("wait_swap", "wait_new"):
            return
        if self._host.busy:
            return
        if self._poll_stuck():
            return
        if self._swap_auto.state.phase == "wait_new":
            now = time.time()
            tick = evaluate_wait_new_tick(
                wait_new_started_at=self._swap_auto.state.wait_new_started_at,
                last_heartbeat_at=self._swap_auto.state.last_heartbeat_at,
                now=now,
                timeout_s=SWAP_NEW_BOARD_TIMEOUT_S,
                heartbeat_s=SWAP_WAIT_NEW_HEARTBEAT_S,
                status_text_fn=lambda: self._swap_auto.wait_new_status_text(now, SWAP_NEW_BOARD_TIMEOUT_S),
            )
            if tick.timed_out:
                self._session.stop_poll_timer()
                self._log("error", "等待新板已超过 2 小时")
                self._host.request_critical("超时", "等待新板已超过 2 小时，自动流程已停止。")
                self._session.reset(switch_manual=True)
                return
            if tick.heartbeat_message:
                self._swap_auto.state.last_heartbeat_at = now
                self._log("info", tick.heartbeat_message)
            if tick.refresh_status:
                self._session.update_status()
        phase = self._swap_auto.state.phase
        self._swap_auto.state.poll_in_flight = True
        self._swap_auto.state.poll_started_at = time.time()
        bmc_ip = self._conn.bmc_ip
        old_user, old_pwd = self._old_credentials()
        new_user, new_pwd = self._new_credentials()
        cached = self._swap_auto.state.old_fingerprint

        def job(_log: LogCallback):
            return run_swap_poll_job(phase, old_user, old_pwd, new_user, new_pwd, bmc_ip, cached, _log)

        def done(result: object):
            self._release_poll()
            if self._swap_auto.state.mode != "auto":
                return
            transition = apply_poll_result(
                current_phase=self._swap_auto.state.phase,
                result=result,
                offline_streak=self._swap_auto.state.offline_streak,
                offline_streak_threshold=SWAP_OFFLINE_STREAK,
                now=time.time(),
            )
            if transition is None:
                return
            self._swap_auto.state.offline_streak = transition.offline_streak
            if transition.wait_new_started_at is not None:
                self._swap_auto.state.wait_new_started_at = transition.wait_new_started_at
            if transition.last_heartbeat_at is not None:
                self._swap_auto.state.last_heartbeat_at = transition.last_heartbeat_at
            for level, message in transition.log_messages:
                self._log(level, message)
            if transition.next_phase:
                self._session.set_phase(transition.next_phase)
            if transition.stop_poll:
                self._session.stop_poll_timer()
            if transition.start_clone:
                self.start_clone()

        self._host.run_worker(job, done, on_error=lambda _m: self._release_poll())

    def start_clone(self) -> None:
        sn = self._progress.old_board_sn.strip()
        user, pwd = self._new_credentials()
        candidates = list_step1_backups(sn)
        if not candidates:
            self._log("error", f"未找到 SN={sn} 的 FRU 备份")
            self._host.request_critical("未找到备份", f"未找到 SN={sn} 的 FRU 备份。")
            self._session.set_phase("wait_new")
            self._session.start_poll_timer()
            return
        old_bin_path = os.path.join(BACKUP_DIR, candidates[-1])
        self._log("info", f"使用备份: {candidates[-1]}")
        self._host.set_busy(True)
        self._session.set_phase("cloning")
        bmc_ip = self._conn.bmc_ip

        def job(log: LogCallback):
            return run_step2_job(sn, user, pwd, bmc_ip, old_bin_path, log)

        self._host.run_worker(job, self._on_clone_done, log_tab="fru")

    def _on_clone_done(self, result: object) -> None:
        self._host.set_busy(False)
        self._conn.apply_bmc_state_from_result(result)
        if isinstance(result, dict) and result.get("ok"):
            self._progress.set_step2_done(True)
            self._progress.set_new_board_serial_backup(result.get("serial"))
            self._progress.set_new_board_fru_backup_path(result.get("rollback") or None)
            self._log("success", f"自动换板完成，Board Serial: {self._progress.new_board_serial_backup}")
            self._session.clear_session()
            self._session.set_phase("done")
            QTimer.singleShot(
                3000,
                lambda: self._session.set_phase("idle") if self._swap_auto.state.mode == "auto" else None,
            )
            self._progress.emit_progress_step()
            self._progress.refresh_capabilities()
        else:
            data = result if isinstance(result, dict) else {}
            self._host.request_critical(data.get("title", "失败"), data.get("message", "自动克隆失败。"))
            self._session.set_phase("wait_new")
            self._session.start_poll_timer()
