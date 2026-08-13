"""FRU editor ViewModel."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.presentation.controller import OpsController
from frutool.presentation.viewmodels._relay import relay


class FruViewModel(QObject):
    capabilitiesChanged = pyqtSignal()

    def __init__(self, ops: OpsController, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._ops = ops
        relay(ops, "capabilitiesChanged", self, self.capabilitiesChanged)

    @pyqtProperty(QObject, constant=True)
    def fruFieldModelProp(self) -> QObject:
        return self._ops.fru_field_model

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canFruWrite(self) -> bool:
        return self._ops.canFruWrite

    @pyqtSlot()
    def doFruReset(self) -> None:
        self._ops.fru_field_model.clearAllValues()

    @pyqtSlot()
    def doFruBatchWrite(self) -> None:
        self._ops.doFruBatchWrite()
