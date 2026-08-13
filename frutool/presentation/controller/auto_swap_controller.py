"""Auto swap controller facade — session + workflow."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.presentation.controller.auto_swap_session import AutoSwapSessionController
from frutool.presentation.controller.auto_swap_workflow import AutoSwapWorkflow
from frutool.presentation.controller.base import ApplicationHost
from frutool.presentation.controller.conn_controller import ConnController
from frutool.presentation.controller.swap_progress import SwapProgress
from frutool.presentation.services import SwapAutoService


class AutoSwapController(QObject):
    """Facade for automatic board swap — delegates to session and workflow."""

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
        self._session = AutoSwapSessionController(host, conn, progress, self)
        self._workflow = AutoSwapWorkflow(self._session)
        self._session.bind_workflow(self._workflow)

        self._session.swapModeChanged.connect(self.swapModeChanged.emit)
        self._session.swapAutoPhaseChanged.connect(self.swapAutoPhaseChanged.emit)
        self._session.swapAutoStatusChanged.connect(self.swapAutoStatusChanged.emit)

    @property
    def swap_auto(self) -> SwapAutoService:
        return self._session.swap_auto

    def has_running_auto_phase(self) -> bool:
        return self._session.has_running_auto_phase()

    @pyqtProperty(str, notify=swapModeChanged)
    def swapMode(self) -> str:
        return self._session.swapMode

    @pyqtProperty(str, notify=swapAutoPhaseChanged)
    def swapAutoPhase(self) -> str:
        return self._session.swapAutoPhase

    @pyqtProperty(str, notify=swapAutoStatusChanged)
    def swapAutoStatus(self) -> str:
        return self._session.swapAutoStatus

    @pyqtProperty(str, notify=swapAutoStatusChanged)
    def swapAutoStatusEn(self) -> str:
        return self._session.swapAutoStatusEn

    @pyqtSlot(str)
    def setSwapMode(self, mode: str) -> None:
        self._session.setSwapMode(mode)

    def persist_session(self) -> None:
        self._session.persist_session()

    def clear_session(self) -> None:
        self._session.clear_session()

    def clear_runtime_state(self) -> None:
        self._session.clear_runtime_state()

    def restore_session(self) -> None:
        self._session.restore_session()

    def on_bmc_online_changed(self, online: bool) -> None:
        self._session.on_bmc_online_changed(online)

    @pyqtSlot(str, bool)
    def snConfirmResponse(self, dialog_id: str, accepted: bool) -> None:
        self._session.snConfirmResponse(dialog_id, accepted)

    def sn_confirm_response(self, dialog_id: str, accepted: bool) -> None:
        self._session.sn_confirm_response(dialog_id, accepted)

    def shutdown(self) -> None:
        self._session.shutdown()

    def reset(self, *, keep_progress: bool = False, switch_manual: bool = False) -> None:
        self._session.reset(keep_progress=keep_progress, switch_manual=switch_manual)

    def update_status(self) -> None:
        self._session.update_status()
