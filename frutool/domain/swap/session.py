"""Pure swap session persistence (no Qt)."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Optional

RESUMABLE_AUTO_PHASES = frozenset({"sn_confirm", "exporting", "wait_swap", "wait_new", "cloning"})

PHASE_LABELS = {
    "wait_swap": "等待换板",
    "wait_new": "等待新板",
    "sn_confirm": "核对 SN",
    "exporting": "导出中",
    "cloning": "克隆中",
}


def is_resumable(swap_mode: str, auto_phase: str) -> bool:
    return swap_mode == "auto" and auto_phase in RESUMABLE_AUTO_PHASES


def should_discard_loaded(data: dict[str, Any]) -> bool:
    phase = str(data.get("swap_auto_phase", "idle"))
    if data.get("step2_done") or phase == "done":
        return True
    return data.get("swap_mode") != "auto"


def phase_label(phase: str) -> str:
    return PHASE_LABELS.get(phase, phase)


def build_session_payload(
    *,
    auto_phase: str,
    sn: str,
    step1_done: bool,
    step2_done: bool,
    old_fingerprint: Optional[dict[str, Any]],
    wait_new_started_at: Optional[float],
    last_export_bin: Optional[str],
    new_board_fru_backup_path: Optional[str],
) -> dict[str, Any]:
    wait_new_iso = None
    if wait_new_started_at is not None:
        wait_new_iso = datetime.fromtimestamp(wait_new_started_at).isoformat(timespec="seconds")
    return {
        "version": 1,
        "swap_mode": "auto",
        "swap_auto_phase": auto_phase,
        "sn": sn.strip(),
        "step1_done": step1_done,
        "step2_done": step2_done,
        "old_fingerprint": old_fingerprint,
        "wait_new_started_at": wait_new_iso,
        "last_export_bin": last_export_bin,
        "new_board_fru_backup_path": new_board_fru_backup_path,
    }


def normalize_restore_phase(
    phase: str,
    last_export_bin: Optional[str],
    backup_dir: str,
) -> tuple[str, bool]:
    """Return (restore_phase, clear_session). clear_session=True when invalid mid-state."""
    if phase not in ("exporting", "cloning"):
        return phase, False
    if last_export_bin and os.path.isfile(os.path.join(backup_dir, last_export_bin)):
        return "wait_swap", False
    return "idle", True


def parse_wait_new_started_at(iso_value: Optional[str]) -> Optional[float]:
    if not iso_value:
        return None
    try:
        return datetime.fromisoformat(iso_value).timestamp()
    except ValueError:
        return None


def wait_new_remaining_seconds(started_at: Optional[float], now: float, timeout_s: float) -> Optional[float]:
    if started_at is None:
        return None
    return timeout_s - (now - started_at)


def format_wait_new_countdown(remaining_s: float) -> str:
    hours, rem = divmod(int(remaining_s), 3600)
    minutes, seconds = divmod(rem, 60)
    return f"等待新板上线，剩余 {hours}:{minutes:02d}:{seconds:02d}"


def format_wait_new_countdown_en(remaining_s: float) -> str:
    hours, rem = divmod(int(remaining_s), 3600)
    minutes, seconds = divmod(rem, 60)
    return f"Waiting for new board, {hours}:{minutes:02d}:{seconds:02d} left"


def load_session(path: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def save_session(path: str, data: dict[str, Any]) -> Optional[str]:
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        return None
    except OSError as exc:
        return str(exc)


def clear_session(path: str) -> None:
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
