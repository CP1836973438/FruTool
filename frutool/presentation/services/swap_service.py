"""Swap auto-flow session file I/O."""
from __future__ import annotations

from typing import Any, Optional

from frutool.domain.swap import session as swap_session


class SwapSessionService:
    def __init__(self, path: str) -> None:
        self._path = path

    @property
    def path(self) -> str:
        return self._path

    def should_persist(self, swap_mode: str, auto_phase: str) -> bool:
        return swap_session.is_resumable(swap_mode, auto_phase)

    def persist(
        self,
        *,
        auto_phase: str,
        sn: str,
        step1_done: bool,
        step2_done: bool,
        old_fingerprint: Optional[dict[str, Any]],
        wait_new_started_at: Optional[float],
        last_export_bin: Optional[str],
        new_board_fru_backup_path: Optional[str],
    ) -> Optional[str]:
        data = swap_session.build_session_payload(
            auto_phase=auto_phase,
            sn=sn,
            step1_done=step1_done,
            step2_done=step2_done,
            old_fingerprint=old_fingerprint,
            wait_new_started_at=wait_new_started_at,
            last_export_bin=last_export_bin,
            new_board_fru_backup_path=new_board_fru_backup_path,
        )
        return swap_session.save_session(self._path, data)

    def clear(self) -> None:
        swap_session.clear_session(self._path)

    def load(self) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        return swap_session.load_session(self._path)
