"""Auto swap phase status text (no Qt)."""
from __future__ import annotations

AUTO_PHASE_STATUS: dict[str, str] = {
    "idle": "等待 BMC 上线（ping 通后自动读取旧板 FRU）…",
    "sn_detect": "正在读取旧板 FRU…",
    "sn_confirm": "请核对服务器 SN 并确认导出",
    "exporting": "正在导出 FRU 备份…",
    "wait_swap": "FRU 已导出，等待旧板离线（请换板）…",
    "cloning": "检测到新板，正在克隆 FRU 并还原新板 SN/PN…",
    "done": "自动换板已完成",
}

AUTO_PHASE_STATUS_EN: dict[str, str] = {
    "idle": "Waiting for BMC (auto-read FRU on ping)…",
    "sn_detect": "Reading old board FRU…",
    "sn_confirm": "Confirm server SN and export",
    "exporting": "Exporting FRU backup…",
    "wait_swap": "FRU exported, waiting for old board offline (swap now)…",
    "cloning": "New board detected, cloning FRU and restoring new-board SN/PN…",
    "done": "Auto swap completed",
}

WAIT_NEW_DEFAULT_CN = "旧板已离线，等待新板上线…"
WAIT_NEW_DEFAULT_EN = "Old board offline, waiting for new board…"


def auto_phase_status(phase: str, *, wait_new_text: str = "") -> str:
    if phase == "wait_new":
        return wait_new_text or WAIT_NEW_DEFAULT_CN
    return AUTO_PHASE_STATUS.get(phase, "")


def auto_phase_status_en(phase: str, *, wait_new_text: str = "") -> str:
    if phase == "wait_new":
        return wait_new_text or WAIT_NEW_DEFAULT_EN
    return AUTO_PHASE_STATUS_EN.get(phase, "")
