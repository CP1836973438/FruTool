"""UI capability rules for swap and operations (no Qt)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UiCapabilities:
    progress_step: int
    can_step1: bool
    can_step2: bool
    can_rollback: bool
    can_swap_reset: bool
    can_fru_write: bool
    can_topo_write: bool
    step2_locked: bool


def compute_ui_capabilities(
    *,
    busy: bool,
    step1_done: bool,
    step2_done: bool,
    swap_mode: str,
    swap_phase_running: bool,
    has_rollback_path: bool,
) -> UiCapabilities:
    auto_running = swap_mode == "auto" and swap_phase_running
    progress = 3 if step2_done else (1 if step1_done else 0)
    idle = not busy
    return UiCapabilities(
        progress_step=progress,
        can_step1=idle and not auto_running,
        can_step2=idle and step1_done and not auto_running,
        can_rollback=idle and has_rollback_path,
        can_swap_reset=idle,
        can_fru_write=idle,
        can_topo_write=idle,
        step2_locked=not step1_done,
    )
