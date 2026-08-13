"""PCIe topology ViewModel."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.presentation.controller import OpsController
from frutool.presentation.viewmodels._relay import relay


class TopoViewModel(QObject):
    topoPathChanged = pyqtSignal()
    topoProgressVisibleChanged = pyqtSignal()
    topoMatchMessageChanged = pyqtSignal()
    topoMatchOkChanged = pyqtSignal()
    topoMatchBusyChanged = pyqtSignal()
    topoCandidatesChanged = pyqtSignal()
    topoCatalogChanged = pyqtSignal()
    selectedTopoCandidateIdChanged = pyqtSignal()
    selectedTopoCatalogIdChanged = pyqtSignal()
    catalogFilterChanged = pyqtSignal()
    capabilitiesChanged = pyqtSignal()

    def __init__(self, ops: OpsController, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._ops = ops
        relay(ops, "topoPathChanged", self, self.topoPathChanged)
        relay(ops, "topoProgressVisibleChanged", self, self.topoProgressVisibleChanged)
        relay(ops, "topoMatchMessageChanged", self, self.topoMatchMessageChanged)
        relay(ops, "topoMatchOkChanged", self, self.topoMatchOkChanged)
        relay(ops, "topoMatchBusyChanged", self, self.topoMatchBusyChanged)
        relay(ops, "topoCandidatesChanged", self, self.topoCandidatesChanged)
        relay(ops, "topoCatalogChanged", self, self.topoCatalogChanged)
        relay(ops, "selectedTopoCandidateIdChanged", self, self.selectedTopoCandidateIdChanged)
        relay(ops, "selectedTopoCatalogIdChanged", self, self.selectedTopoCatalogIdChanged)
        relay(ops, "catalogFilterChanged", self, self.catalogFilterChanged)
        relay(ops, "capabilitiesChanged", self, self.capabilitiesChanged)

    @pyqtProperty(str, notify=topoPathChanged)
    def topoPath(self) -> str:
        return self._ops.topoPath

    @pyqtSlot(str)
    def setTopoPath(self, path: str) -> None:
        self._ops.setTopoPath(path)

    @pyqtProperty(bool, notify=topoProgressVisibleChanged)
    def topoProgressVisible(self) -> bool:
        return self._ops.topoProgressVisible

    @pyqtProperty(str, notify=topoMatchMessageChanged)
    def topoMatchMessage(self) -> str:
        return self._ops.topoMatchMessage

    @pyqtProperty(bool, notify=topoMatchOkChanged)
    def topoMatchOk(self) -> bool:
        return self._ops.topoMatchOk

    @pyqtProperty(bool, notify=topoMatchBusyChanged)
    def topoMatchBusy(self) -> bool:
        return self._ops.topoMatchBusy

    @pyqtProperty("QVariantList", notify=topoCandidatesChanged)
    def topoCandidates(self) -> list:
        return self._ops.topoCandidates

    @pyqtProperty("QVariantList", notify=topoCatalogChanged)
    def topoCatalog(self) -> list:
        return self._ops.topoCatalog

    @pyqtProperty(str, notify=selectedTopoCandidateIdChanged)
    def selectedTopoCandidateId(self) -> str:
        return self._ops.selectedTopoCandidateId

    @pyqtProperty(str, notify=selectedTopoCatalogIdChanged)
    def selectedTopoCatalogId(self) -> str:
        return self._ops.selectedTopoCatalogId

    @pyqtProperty(str, notify=catalogFilterChanged)
    def catalogFilter(self) -> str:
        return self._ops.catalogFilter

    @pyqtSlot(str)
    def setCatalogFilter(self, text: str) -> None:
        self._ops.setCatalogFilter(text)

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canTopoWrite(self) -> bool:
        return self._ops.canTopoWrite

    @pyqtProperty(bool, constant=True)
    def demoMode(self) -> bool:
        return self._ops.demoMode

    @pyqtSlot()
    def browseTopoFile(self) -> None:
        self._ops.browseTopoFile()

    @pyqtSlot()
    def doTopoWrite(self) -> None:
        self._ops.doTopoWrite()

    @pyqtSlot(str)
    def selectTopoCandidate(self, entry_id: str) -> None:
        self._ops.selectTopoCandidate(entry_id)

    @pyqtSlot(str)
    def selectTopoCatalogEntry(self, entry_id: str) -> None:
        self._ops.selectTopoCatalogEntry(entry_id)
