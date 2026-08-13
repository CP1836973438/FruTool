"""Auto board-swap orchestration helpers (state + session, no Qt)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from frutool.domain.ipmi import FruFingerprint
from frutool.domain.swap.auto import auto_phase_running
from frutool.domain.swap.session import format_wait_new_countdown, format_wait_new_countdown_en, wait_new_remaining_seconds
from frutool.domain.swap.status import auto_phase_status, auto_phase_status_en
from frutool.presentation.services.swap_service import SwapSessionService


@dataclass
class SwapAutoState:
    mode: str = "manual"
    phase: str = "idle"
    old_fingerprint: Optional[FruFingerprint] = None
    prev_bmc_online: bool = False
    offline_streak: int = 0
    wait_new_started_at: Optional[float] = None
    poll_in_flight: bool = False
    poll_started_at: Optional[float] = None
    last_heartbeat_at: Optional[float] = None
    last_export_bin: Optional[str] = None
    pending_sn_confirm_fp: Optional[FruFingerprint] = None


class SwapAutoService:
    def __init__(self, session: SwapSessionService) -> None:
        self.state = SwapAutoState()
        self._session = session

    def phase_running(self) -> bool:
        return auto_phase_running(self.state.phase)

    def status_text(self, *, wait_new_text: str) -> str:
        if self.state.mode != "auto":
            return ""
        return auto_phase_status(self.state.phase, wait_new_text=wait_new_text)

    def status_text_en(self, *, wait_new_text: str) -> str:
        if self.state.mode != "auto":
            return ""
        return auto_phase_status_en(self.state.phase, wait_new_text=wait_new_text)

    def wait_new_status_text(self, now: float, timeout_s: float) -> str:
        if not self.state.wait_new_started_at:
            return "旧板已离线，等待新板上线…"
        remaining = wait_new_remaining_seconds(self.state.wait_new_started_at, now, timeout_s)
        if remaining is None:
            return "旧板已离线，等待新板上线…"
        return format_wait_new_countdown(max(0, remaining))

    def wait_new_status_text_en(self, now: float, timeout_s: float) -> str:
        if not self.state.wait_new_started_at:
            return "Old board offline, waiting for new board…"
        remaining = wait_new_remaining_seconds(self.state.wait_new_started_at, now, timeout_s)
        if remaining is None:
            return "Old board offline, waiting for new board…"
        return format_wait_new_countdown_en(max(0, remaining))

    def persist(
        self,
        *,
        closing: bool,
        sn: str,
        step1_done: bool,
        step2_done: bool,
        new_board_fru_backup_path: Optional[str],
    ) -> Optional[str]:
        if closing:
            return None
        if not self._session.should_persist(self.state.mode, self.state.phase):
            self._session.clear()
            return None
        fp = self.state.old_fingerprint.to_dict() if self.state.old_fingerprint else None
        return self._session.persist(
            auto_phase=self.state.phase,
            sn=sn,
            step1_done=step1_done,
            step2_done=step2_done,
            old_fingerprint=fp,
            wait_new_started_at=self.state.wait_new_started_at,
            last_export_bin=self.state.last_export_bin,
            new_board_fru_backup_path=new_board_fru_backup_path,
        )

    def clear_session(self) -> None:
        self._session.clear()

    def load_session(self) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        return self._session.load()

    def reset_runtime(self, *, keep_progress: bool = False) -> None:
        self.state.pending_sn_confirm_fp = None
        self.state.offline_streak = 0
        self.state.poll_in_flight = False
        self.state.poll_started_at = None
        if not keep_progress:
            self.state.wait_new_started_at = None
            self.state.last_heartbeat_at = None

    def set_phase(self, phase: str) -> bool:
        """Return True if progress step should refresh."""
        self.state.phase = phase
        if phase == "wait_swap":
            return True
        if phase in ("sn_confirm", "exporting", "done"):
            return True
        return phase == "idle"
