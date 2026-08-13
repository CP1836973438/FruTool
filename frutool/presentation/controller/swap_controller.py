"""Swap controller facade — composes progress, manual, and auto swap."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.config import SWAP_SESSION_JSON
from frutool.presentation.controller.auto_swap_controller import AutoSwapController
from frutool.presentation.controller.base import ApplicationHost
from frutool.presentation.controller.conn_controller import ConnController
from frutool.presentation.controller.manual_swap_controller import ManualSwapController
from frutool.presentation.controller.swap_progress import SwapProgress
from frutool.presentation.services import SwapAutoService, SwapSessionService, list_step1_backups


class SwapController(QObject):
    """Facade for manual/auto swap — preserves the original public API."""

    step1DoneChanged = pyqtSignal()
    step2DoneChanged = pyqtSignal()
    swapModeChanged = pyqtSignal()
    swapAutoPhaseChanged = pyqtSignal()
    swapAutoStatusChanged = pyqtSignal()
    oldBoardSnChanged = pyqtSignal()
    lastExportBinChanged = pyqtSignal()
    newBoardSerialChanged = pyqtSignal()
    progressStepChanged = pyqtSignal()
    capabilitiesChanged = pyqtSignal()

    def __init__(
        self,
        host: ApplicationHost,
        conn: ConnController,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        if host.swap_auto is None:
            host.swap_auto = SwapAutoService(SwapSessionService(SWAP_SESSION_JSON))

        self._progress = SwapProgress(host, host.swap_auto, self)
        self.auto = AutoSwapController(host, conn, self._progress, self)
        self.manual = ManualSwapController(host, conn, self._progress, self.auto)

        for src, dst in (
            (self._progress.step1DoneChanged, self.step1DoneChanged),
            (self._progress.step2DoneChanged, self.step2DoneChanged),
            (self._progress.oldBoardSnChanged, self.oldBoardSnChanged),
            (self._progress.newBoardSerialChanged, self.newBoardSerialChanged),
            (self._progress.progressStepChanged, self.progressStepChanged),
            (self._progress.capabilitiesChanged, self.capabilitiesChanged),
            (self.auto.swapModeChanged, self.swapModeChanged),
            (self.auto.swapAutoPhaseChanged, self.swapAutoPhaseChanged),
            (self.auto.swapAutoStatusChanged, self.swapAutoStatusChanged),
        ):
            src.connect(dst.emit)

        for sig in (
            self.step1DoneChanged,
            self.step2DoneChanged,
            self.oldBoardSnChanged,
            self.swapAutoPhaseChanged,
            self.swapAutoStatusChanged,
        ):
            sig.connect(self.lastExportBinChanged.emit)

    def refresh_capabilities(self) -> None:
        self._progress.refresh_capabilities()

    # --- Progress properties ---

    @pyqtProperty(int, notify=progressStepChanged)
    def progressStep(self) -> int:
        return self._progress.progressStep

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canStep1(self) -> bool:
        return self._progress.canStep1

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canStep2(self) -> bool:
        return self._progress.canStep2

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canRollback(self) -> bool:
        return self._progress.canRollback

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canSwapReset(self) -> bool:
        return self._progress.canSwapReset

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canFruWrite(self) -> bool:
        return self._progress.canFruWrite

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canTopoWrite(self) -> bool:
        return self._progress.canTopoWrite

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def step2Locked(self) -> bool:
        return self._progress.step2Locked

    @pyqtProperty(bool, notify=step1DoneChanged)
    def step1Done(self) -> bool:
        return self._progress.step1Done

    @pyqtProperty(bool, notify=step2DoneChanged)
    def step2Done(self) -> bool:
        return self._progress.step2Done

    @pyqtProperty(str, notify=swapModeChanged)
    def swapMode(self) -> str:
        return self.auto.swapMode

    @pyqtProperty(str, notify=swapAutoPhaseChanged)
    def swapAutoPhase(self) -> str:
        return self.auto.swapAutoPhase

    @pyqtProperty(str, notify=swapAutoStatusChanged)
    def swapAutoStatus(self) -> str:
        return self.auto.swapAutoStatus

    @pyqtProperty(str, notify=swapAutoStatusChanged)
    def swapAutoStatusEn(self) -> str:
        return self.auto.swapAutoStatusEn

    @pyqtProperty(str, notify=oldBoardSnChanged)
    def oldBoardSn(self) -> str:
        return self._progress.oldBoardSn

    @pyqtProperty(str, notify=lastExportBinChanged)
    def lastExportBin(self) -> str:
        return self._resolve_last_export_bin()

    @pyqtProperty(str, notify=newBoardSerialChanged)
    def newBoardSerial(self) -> str:
        return self._progress.new_board_serial_backup or ""

    def _resolve_last_export_bin(self) -> str:
        last = self.auto.swap_auto.state.last_export_bin
        if last:
            return last
        sn = self._progress.old_board_sn.strip()
        if not sn:
            return ""
        backups = list_step1_backups(sn)
        return backups[-1] if backups else ""

    @pyqtSlot(str)
    def setOldBoardSn(self, sn: str) -> None:
        self._progress.setOldBoardSn(sn)

    def sync_step1_from_backup(self) -> None:
        self._progress.sync_step1_from_backup()

    # --- Manual swap ---

    @pyqtSlot()
    def doStep1(self) -> None:
        self.manual.doStep1()

    @pyqtSlot()
    def doStep2(self) -> None:
        self.manual.doStep2()

    @pyqtSlot()
    def doRollback(self) -> None:
        self.manual.doRollback()

    @pyqtSlot()
    def doSwapReset(self) -> None:
        self.manual.doSwapReset()

    # --- Auto swap ---

    @pyqtSlot(str)
    def setSwapMode(self, mode: str) -> None:
        self.auto.setSwapMode(mode)

    def restore_session(self) -> None:
        self.auto.restore_session()

    def persist_session(self) -> None:
        self.auto.persist_session()

    def on_bmc_online_changed(self, online: bool) -> None:
        self.auto.on_bmc_online_changed(online)

    @pyqtSlot(str, bool)
    def snConfirmResponse(self, dialog_id: str, accepted: bool) -> None:
        self.auto.snConfirmResponse(dialog_id, accepted)

    def sn_confirm_response(self, dialog_id: str, accepted: bool) -> None:
        self.auto.sn_confirm_response(dialog_id, accepted)

    def shutdown_swap(self) -> None:
        self.auto.shutdown()
