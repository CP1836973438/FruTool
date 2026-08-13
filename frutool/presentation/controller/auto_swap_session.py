"""Auto swap session — mode, phase, persist/restore, poll timer."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.config import BACKUP_DIR, SWAP_NEW_BOARD_TIMEOUT_S, SWAP_POLL_INTERVAL_MS, SWAP_SESSION_JSON
from frutool.domain.swap.auto import build_session_restore_plan, restore_prompt_message
from frutool.domain.swap.session import should_discard_loaded
from frutool.presentation.services import SwapAutoService, SwapSessionService, list_step1_backups

if TYPE_CHECKING:
    from frutool.presentation.controller.auto_swap_workflow import AutoSwapWorkflow
    from frutool.presentation.controller.base import ApplicationHost
    from frutool.presentation.controller.conn_controller import ConnController
    from frutool.presentation.controller.swap_progress import SwapProgress


class AutoSwapSessionController(QObject):
    """Auto swap mode/phase state, session file, and poll timer."""

    swapModeChanged = pyqtSignal()
    swapAutoPhaseChanged = pyqtSignal()
    swapAutoStatusChanged = pyqtSignal()

    def __init__(
        self,
        host: ApplicationHost,
        conn: ConnController,
        progress: SwapProgress,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._host = host
        self._conn = conn
        self._progress = progress
        if host.swap_auto is None:
            host.swap_auto = SwapAutoService(SwapSessionService(SWAP_SESSION_JSON))
        self._swap_auto = host.swap_auto
        self._workflow: Optional[AutoSwapWorkflow] = None

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_poll_tick)

    def bind_workflow(self, workflow: AutoSwapWorkflow) -> None:
        self._workflow = workflow

    @property
    def swap_auto(self) -> SwapAutoService:
        return self._swap_auto

    def has_running_auto_phase(self) -> bool:
        return self._swap_auto.state.mode == "auto" and self._swap_auto.phase_running()

    @pyqtProperty(str, notify=swapModeChanged)
    def swapMode(self) -> str:
        return self._swap_auto.state.mode

    @pyqtProperty(str, notify=swapAutoPhaseChanged)
    def swapAutoPhase(self) -> str:
        return self._swap_auto.state.phase

    @pyqtProperty(str, notify=swapAutoStatusChanged)
    def swapAutoStatus(self) -> str:
        now = time.time()
        wait_new = self._swap_auto.wait_new_status_text(now, SWAP_NEW_BOARD_TIMEOUT_S)
        return self._swap_auto.status_text(wait_new_text=wait_new)

    @pyqtProperty(str, notify=swapAutoStatusChanged)
    def swapAutoStatusEn(self) -> str:
        now = time.time()
        wait_new = self._swap_auto.wait_new_status_text_en(now, SWAP_NEW_BOARD_TIMEOUT_S)
        return self._swap_auto.status_text_en(wait_new_text=wait_new)

    @pyqtSlot(str)
    def setSwapMode(self, mode: str) -> None:
        wf = self._workflow
        if wf is None or mode not in ("manual", "auto"):
            return
        if mode == self._swap_auto.state.mode:
            return
        if mode == "manual" and self._swap_auto.phase_running():

            def on_answer(ok: bool):
                if not ok:
                    return
                self.reset(keep_progress=True)
                self._swap_auto.state.mode = "manual"
                self.swapModeChanged.emit()
                self._host.log("info", "已切换为手动换板模式")
                self.update_status()
                self._progress.refresh_capabilities()

            self._host.request_question(
                "切换为手动",
                "自动换板正在进行中，切换为手动将停止自动流程（已导出的备份保留）。是否继续？",
                on_answer,
            )
            return
        self._swap_auto.state.mode = mode
        self.swapModeChanged.emit()
        if mode == "auto":
            self.auto_log("info", "已切换为自动模式")
            if self._progress.step1_done and not self._progress.step2_done:
                sn = self._progress.old_board_sn.strip()
                backups = list_step1_backups(sn)
                if backups:
                    self._swap_auto.state.last_export_bin = backups[-1]
                if not self._swap_auto.state.old_fingerprint:
                    wf.ensure_fingerprint_async()
                self.set_phase("wait_swap")
                self.start_poll_timer()
            else:
                self.set_phase("idle")
                if self._conn.bmcOnline:
                    wf.start_sn_detect()
        else:
            self._host.log("info", "已切换为手动换板模式")
            self.update_status()
        self._progress.refresh_capabilities()

    def persist_session(self) -> None:
        err = self._swap_auto.persist(
            closing=self._host.closing,
            sn=self._progress.old_board_sn,
            step1_done=self._progress.step1_done,
            step2_done=self._progress.step2_done,
            new_board_fru_backup_path=self._progress.new_board_fru_backup_path,
        )
        if err:
            self.auto_log("warning", f"无法保存会话状态: {err}")

    def clear_session(self) -> None:
        self._swap_auto.clear_session()

    def clear_runtime_state(self) -> None:
        self._swap_auto.state.old_fingerprint = None
        self._swap_auto.state.last_export_bin = None
        self._swap_auto.reset_runtime()

    def restore_session(self) -> None:
        wf = self._workflow
        if wf is None:
            return
        data, err = self._swap_auto.load_session()
        if err:
            self.auto_log("warning", f"无法读取会话文件: {err}")
            self.clear_session()
            return
        if data is None:
            return
        if should_discard_loaded(data):
            self.clear_session()
            return
        plan = build_session_restore_plan(
            data, now=time.time(), timeout_s=SWAP_NEW_BOARD_TIMEOUT_S, backup_dir=BACKUP_DIR
        )
        if plan.timed_out:
            self._host.request_warning("会话已超时", "等待新板已超过 2 小时，会话已清除。")
            self.clear_session()
            return

        def on_restore(ok: bool):
            if not ok:
                self.clear_session()
                return
            if plan.sn:
                self._progress.set_old_board_sn(plan.sn)
            if plan.fingerprint:
                self._swap_auto.state.old_fingerprint = plan.fingerprint
            self._progress.set_step1_done(plan.step1_done)
            self._swap_auto.state.last_export_bin = plan.last_export_bin
            self._progress.set_new_board_fru_backup_path(plan.new_board_fru_backup_path)
            self._swap_auto.state.wait_new_started_at = plan.wait_new_started_at
            if plan.clear_invalid_mid_state:
                self.auto_log("warning", "中间态无有效备份，已重置为空闲")
                self.clear_session()
            elif plan.restore_phase == "wait_swap" and str(data.get("swap_auto_phase", "")) in (
                "exporting",
                "cloning",
            ):
                self.auto_log("info", "从中间态恢复为等待换板")
            self._swap_auto.state.mode = "auto"
            self.swapModeChanged.emit()
            self.auto_log("info", f"已恢复自动换板会话，阶段={plan.phase_label}")
            self.set_phase(plan.restore_phase)
            if plan.show_sn_confirm and plan.fingerprint:
                wf.show_sn_confirm(plan.fingerprint)
            elif plan.start_poll:
                self.start_poll_timer()
            elif plan.start_sn_detect and self._conn.bmcOnline:
                wf.start_sn_detect()
            self._progress.refresh_capabilities()

        self._host.request_question(
            "恢复自动换板",
            restore_prompt_message(plan.sn, plan.phase_label),
            on_restore,
        )

    def reset(self, *, keep_progress: bool = False, switch_manual: bool = False) -> None:
        self.stop_poll_timer()
        self._swap_auto.state.pending_sn_confirm_fp = None
        self._swap_auto.state.offline_streak = 0
        self._swap_auto.state.poll_in_flight = False
        self._swap_auto.state.poll_started_at = None
        if not keep_progress:
            self._swap_auto.state.wait_new_started_at = None
            self._swap_auto.state.last_heartbeat_at = None
        self.set_phase("idle")
        if switch_manual:
            self._swap_auto.state.mode = "manual"
            self.swapModeChanged.emit()
            self.update_status()
        if not keep_progress:
            self.clear_session()

    def update_status(self) -> None:
        self.swapAutoStatusChanged.emit()

    def on_bmc_online_changed(self, online: bool) -> None:
        wf = self._workflow
        if wf is None:
            return
        prev = self._swap_auto.state.prev_bmc_online
        self._swap_auto.state.prev_bmc_online = online
        if self._swap_auto.state.mode != "auto":
            return
        if online and not prev and self._swap_auto.state.phase == "idle":
            wf.start_sn_detect()

    @pyqtSlot(str, bool)
    def snConfirmResponse(self, dialog_id: str, accepted: bool) -> None:
        self.sn_confirm_response(dialog_id, accepted)

    def sn_confirm_response(self, dialog_id: str, accepted: bool) -> None:
        wf = self._workflow
        if wf is None:
            return
        self._host.dialog_service.respond(dialog_id, accepted)
        fp = self._swap_auto.state.pending_sn_confirm_fp
        self._swap_auto.state.pending_sn_confirm_fp = None
        if not accepted or fp is None:
            if fp is not None:
                self.auto_log("info", "已取消自动流程")
                self.reset(switch_manual=True)
            return
        self.auto_log("info", "SN 已确认，开始导出 FRU")
        wf.start_export()

    def shutdown(self) -> None:
        self.persist_session()
        self.stop_poll_timer()
        self._swap_auto.state.pending_sn_confirm_fp = None

    def auto_log(self, level: str, message: str) -> None:
        self._host.log(level, f"[Auto] {message}")

    def set_phase(self, phase: str) -> None:
        self._swap_auto.state.phase = phase
        self.swapAutoPhaseChanged.emit()
        self.update_status()
        self.persist_session()
        self._progress.refresh_capabilities()
        if self._swap_auto.set_phase(phase) or (phase == "idle" and not self._progress.step2_done):
            self._progress.emit_progress_step()

    def stop_poll_timer(self) -> None:
        self._poll_timer.stop()

    def start_poll_timer(self) -> None:
        self._poll_timer.start(SWAP_POLL_INTERVAL_MS)

    def _on_poll_tick(self) -> None:
        if self._workflow is not None:
            self._workflow.on_poll_tick()
