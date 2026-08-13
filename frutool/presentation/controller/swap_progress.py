"""Shared swap progress state and UI capabilities."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.presentation.services import SwapAutoService, compute_ui_capabilities, list_step1_backups

if TYPE_CHECKING:
    from frutool.presentation.controller.base import ApplicationHost


class SwapProgress(QObject):
    """Manual swap progress (step 1/2, SN, rollback path) and capability flags."""

    step1DoneChanged = pyqtSignal()
    step2DoneChanged = pyqtSignal()
    oldBoardSnChanged = pyqtSignal()
    newBoardSerialChanged = pyqtSignal()
    progressStepChanged = pyqtSignal()
    capabilitiesChanged = pyqtSignal()

    def __init__(self, host: ApplicationHost, swap_auto: SwapAutoService, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._host = host
        self._swap_auto = swap_auto
        self._step1_done = False
        self._step2_done = False
        self._last_synced_sn = ""
        self._new_board_serial_backup: Optional[str] = None
        self._new_board_fru_backup_path: Optional[str] = None
        self._old_board_sn = ""

    # --- Mutable state (used by manual/auto controllers) ---

    @property
    def step1_done(self) -> bool:
        return self._step1_done

    @property
    def step2_done(self) -> bool:
        return self._step2_done

    @property
    def old_board_sn(self) -> str:
        return self._old_board_sn

    @property
    def last_synced_sn(self) -> str:
        return self._last_synced_sn

    @property
    def new_board_serial_backup(self) -> Optional[str]:
        return self._new_board_serial_backup

    @property
    def new_board_fru_backup_path(self) -> Optional[str]:
        return self._new_board_fru_backup_path

    def set_step1_done(self, done: bool) -> None:
        if done == self._step1_done:
            return
        self._step1_done = done
        self.step1DoneChanged.emit()

    def set_step2_done(self, done: bool) -> None:
        if done == self._step2_done:
            return
        self._step2_done = done
        self.step2DoneChanged.emit()

    def set_old_board_sn(self, sn: str, *, emit: bool = True) -> None:
        if sn == self._old_board_sn:
            return
        self._old_board_sn = sn
        if emit:
            self.oldBoardSnChanged.emit()

    def set_last_synced_sn(self, sn: str) -> None:
        self._last_synced_sn = sn

    def set_new_board_serial_backup(self, serial: Optional[str]) -> None:
        if serial == self._new_board_serial_backup:
            return
        self._new_board_serial_backup = serial
        self.newBoardSerialChanged.emit()

    def set_new_board_fru_backup_path(self, path: Optional[str]) -> None:
        self._new_board_fru_backup_path = path

    def clear_rollback_state(self) -> None:
        self._new_board_fru_backup_path = None
        if self._new_board_serial_backup is not None:
            self._new_board_serial_backup = None
            self.newBoardSerialChanged.emit()

    def clear_all_progress(self) -> None:
        self._step1_done = False
        self.step1DoneChanged.emit()
        self._step2_done = False
        self.step2DoneChanged.emit()
        self._last_synced_sn = ""
        self._new_board_serial_backup = None
        self.newBoardSerialChanged.emit()
        self._new_board_fru_backup_path = None
        self._old_board_sn = ""
        self.oldBoardSnChanged.emit()

    def refresh_capabilities(self) -> None:
        self.capabilitiesChanged.emit()

    def _ui_capabilities(self):
        return compute_ui_capabilities(
            busy=self._host.busy,
            step1_done=self._step1_done,
            step2_done=self._step2_done,
            swap_mode=self._swap_auto.state.mode,
            swap_phase_running=self._swap_auto.phase_running(),
            has_rollback_path=bool(self._new_board_fru_backup_path),
        )

    @pyqtProperty(int, notify=progressStepChanged)
    def progressStep(self) -> int:
        return self._ui_capabilities().progress_step

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canStep1(self) -> bool:
        return self._ui_capabilities().can_step1

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canStep2(self) -> bool:
        return self._ui_capabilities().can_step2

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canRollback(self) -> bool:
        return self._ui_capabilities().can_rollback

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canSwapReset(self) -> bool:
        return self._ui_capabilities().can_swap_reset

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canFruWrite(self) -> bool:
        return self._ui_capabilities().can_fru_write

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canTopoWrite(self) -> bool:
        return self._ui_capabilities().can_topo_write

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def step2Locked(self) -> bool:
        return self._ui_capabilities().step2_locked

    @pyqtProperty(bool, notify=step1DoneChanged)
    def step1Done(self) -> bool:
        return self._step1_done

    @pyqtProperty(bool, notify=step2DoneChanged)
    def step2Done(self) -> bool:
        return self._step2_done

    @pyqtProperty(str, notify=oldBoardSnChanged)
    def oldBoardSn(self) -> str:
        return self._old_board_sn

    @pyqtSlot(str)
    def setOldBoardSn(self, sn: str) -> None:
        text = sn.strip()
        if text == self._old_board_sn:
            return
        self.set_old_board_sn(text)
        if text != self._last_synced_sn:
            self.set_step2_done(False)
            self.clear_rollback_state()
            self._last_synced_sn = text
            self.refresh_capabilities()
        self.sync_step1_from_backup()

    def sync_step1_from_backup(self) -> None:
        sn = self._old_board_sn.strip()
        backups = list_step1_backups(sn)
        had_step1 = self._step1_done
        if backups:
            self.set_step1_done(True)
            if not self._step2_done:
                self.progressStepChanged.emit()
            if not had_step1 and sn:
                self._host.log("info", f"已找到 FRU 备份 {backups[-1]}，可直接进行步骤 2")
        elif not self._step2_done:
            self.set_step1_done(False)
            self.progressStepChanged.emit()
        self.refresh_capabilities()

    def emit_progress_step(self) -> None:
        self.progressStepChanged.emit()
