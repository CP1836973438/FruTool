"""Dialog host ViewModel."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from frutool.presentation.controller import ApplicationController


class DialogViewModel(QObject):
    dialogRequested = pyqtSignal(str)
    aboutRequested = pyqtSignal()

    def __init__(self, ctrl: ApplicationController, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._ctrl = ctrl
        ctrl.dialogRequested.connect(self.dialogRequested.emit)
        ctrl.aboutRequested.connect(self.aboutRequested.emit)

    @pyqtSlot(str, bool)
    def dialogResponse(self, dialog_id: str, accepted: bool) -> None:
        self._ctrl.dialogResponse(dialog_id, accepted)

    @pyqtSlot(str, bool)
    def snConfirmResponse(self, dialog_id: str, accepted: bool) -> None:
        self._ctrl.snConfirmResponse(dialog_id, accepted)
