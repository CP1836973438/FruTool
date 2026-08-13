"""Auto swap worker jobs and poll transition logic (no Qt)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from frutool.config import BACKUP_DIR, LogCallback
from frutool.domain.ipmi import FruFingerprint, capture_fru_fingerprint, probe_fru_list
from frutool.domain.swap.session import (
    normalize_restore_phase,
    parse_wait_new_started_at,
    phase_label,
    wait_new_remaining_seconds,
)

DialogError = tuple[str, str, str]


def auto_phase_running(phase: str) -> bool:
    return phase not in ("idle", "done")


def validate_auto_export(sn: str, user: str, pwd: str, ipmitool_path: str = "") -> Optional[DialogError]:
    if not sn.strip():
        return ("导出失败", "服务器 SN 为空，无法导出", "critical")
    if not user or not pwd:
        return ("导出失败", "旧板凭据未配置", "critical")
    from frutool.config import ipmitool_install_hint, resolve_ipmitool_path

    if not resolve_ipmitool_path(refresh=True):
        return ("导出失败", ipmitool_install_hint(), "critical")
    return None


def run_sn_detect_job(user: str, pwd: str, bmc_ip: str, _log: LogCallback) -> dict[str, Any]:
    ok, out = probe_fru_list(user, pwd, bmc_ip)
    if not ok:
        return {"ok": False}
    fp = capture_fru_fingerprint(out)
    if not fp:
        return {"ok": False}
    return {"ok": True, "fingerprint": fp}


def run_capture_fingerprint_job(user: str, pwd: str, bmc_ip: str, _log: LogCallback) -> Optional[FruFingerprint]:
    ok, out = probe_fru_list(user, pwd, bmc_ip)
    if not ok:
        return None
    return capture_fru_fingerprint(out)


def run_swap_poll_job(
    phase: str,
    old_user: str,
    old_pwd: str,
    new_user: str,
    new_pwd: str,
    bmc_ip: str,
    cached: Optional[FruFingerprint],
    _log: LogCallback,
) -> dict[str, Any]:
    if phase == "wait_swap":
        ok, out = probe_fru_list(old_user, old_pwd, bmc_ip)
        if ok and cached:
            fp = capture_fru_fingerprint(out)
            if fp and fp.board_serial == cached.board_serial:
                return {"phase": "wait_swap", "streak": 0}
        return {"phase": "wait_swap", "streak": 1}
    ok, out = probe_fru_list(new_user, new_pwd, bmc_ip)
    if ok and cached:
        fp = capture_fru_fingerprint(out)
        if fp and fp.board_serial != cached.board_serial:
            return {"phase": "wait_new", "action": "clone"}
    return {"phase": "wait_new", "action": "wait"}


@dataclass
class WaitNewTick:
    timed_out: bool = False
    heartbeat_message: Optional[str] = None
    refresh_status: bool = False


def evaluate_wait_new_tick(
    *,
    wait_new_started_at: Optional[float],
    last_heartbeat_at: Optional[float],
    now: float,
    timeout_s: float,
    heartbeat_s: float,
    status_text_fn,
) -> WaitNewTick:
    tick = WaitNewTick()
    if wait_new_started_at is not None:
        elapsed = now - wait_new_started_at
        if elapsed >= timeout_s:
            tick.timed_out = True
            return tick
    if last_heartbeat_at is None or now - last_heartbeat_at >= heartbeat_s:
        tick.heartbeat_message = status_text_fn()
        tick.refresh_status = True
    else:
        tick.refresh_status = True
    return tick


@dataclass
class PollDoneTransition:
    offline_streak: int
    wait_new_started_at: Optional[float] = None
    last_heartbeat_at: Optional[float] = None
    next_phase: Optional[str] = None
    stop_poll: bool = False
    start_clone: bool = False
    log_messages: list[tuple[str, str]] = field(default_factory=list)


def apply_poll_result(
    *,
    current_phase: str,
    result: object,
    offline_streak: int,
    offline_streak_threshold: int,
    now: float,
) -> Optional[PollDoneTransition]:
    if not isinstance(result, dict):
        return None
    transition = PollDoneTransition(offline_streak=offline_streak)
    if result.get("phase") == "wait_swap" and current_phase == "wait_swap":
        if result.get("streak", 0):
            transition.offline_streak = offline_streak + 1
            if transition.offline_streak >= offline_streak_threshold:
                transition.offline_streak = 0
                transition.wait_new_started_at = now
                transition.last_heartbeat_at = now
                transition.next_phase = "wait_new"
                transition.log_messages.append(
                    ("success", "旧板 FRU 已离线，开始等待新板（最长 2 小时）")
                )
        else:
            transition.offline_streak = 0
        return transition
    if result.get("phase") == "wait_new" and current_phase == "wait_new":
        if result.get("action") == "clone":
            transition.stop_poll = True
            transition.start_clone = True
            transition.log_messages.append(("success", "检测到新板，开始自动克隆"))
        return transition
    return None


@dataclass
class SessionRestorePlan:
    sn: str
    phase_label: str
    restore_phase: str
    clear_session: bool = False
    clear_invalid_mid_state: bool = False
    timed_out: bool = False
    show_sn_confirm: bool = False
    start_poll: bool = False
    start_sn_detect: bool = False
    fingerprint: Optional[FruFingerprint] = None
    step1_done: bool = False
    last_export_bin: Optional[str] = None
    new_board_fru_backup_path: Optional[str] = None
    wait_new_started_at: Optional[float] = None


def build_session_restore_plan(
    data: dict[str, Any],
    *,
    now: float,
    timeout_s: float,
    backup_dir: str,
) -> SessionRestorePlan:
    phase = str(data.get("swap_auto_phase", "idle"))
    sn = str(data.get("sn", "")).strip()
    fp_data = data.get("old_fingerprint")
    fingerprint = FruFingerprint.from_dict(fp_data) if fp_data else None
    wait_new_started_at = parse_wait_new_started_at(data.get("wait_new_started_at"))
    last_export_bin = data.get("last_export_bin")
    restore_phase, clear_invalid = normalize_restore_phase(phase, last_export_bin, backup_dir)
    plan = SessionRestorePlan(
        sn=sn,
        phase_label=phase_label(phase),
        restore_phase=restore_phase,
        clear_invalid_mid_state=clear_invalid,
        fingerprint=fingerprint,
        step1_done=bool(data.get("step1_done")),
        last_export_bin=last_export_bin,
        new_board_fru_backup_path=data.get("new_board_fru_backup_path") or None,
        wait_new_started_at=wait_new_started_at,
    )
    if restore_phase == "wait_new" and wait_new_started_at is not None:
        remaining = wait_new_remaining_seconds(wait_new_started_at, now, timeout_s)
        if remaining is not None and remaining <= 0:
            plan.timed_out = True
            plan.clear_session = True
            return plan
    plan.show_sn_confirm = restore_phase == "sn_confirm" and fingerprint is not None
    plan.start_poll = restore_phase in ("wait_swap", "wait_new")
    plan.start_sn_detect = restore_phase == "idle"
    return plan


def build_sn_confirm_dialog(
    fingerprint: FruFingerprint,
    *,
    dialog_id: str,
    timeout_s: int,
) -> dict[str, Any]:
    return {
        "type": "sn_confirm",
        "id": dialog_id,
        "title": "核对服务器 SN",
        "productSerial": fingerprint.product_serial or "",
        "boardSerial": fingerprint.board_serial or "",
        "productName": fingerprint.product_name or "",
        "countdown": timeout_s if fingerprint.product_serial else 0,
    }


def restore_prompt_message(sn: str, label: str) -> str:
    return f"检测到未完成的自动换板会话。\n\nSN: {sn or '—'}\n阶段: {label}\n\n是否继续？"
