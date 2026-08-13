"""Board swap ViewModel."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.presentation.controller import SwapController
from frutool.presentation.viewmodels._relay import relay


class SwapViewModel(QObject):
    step1DoneChanged = pyqtSignal()
    step2DoneChanged = pyqtSignal()
    swapModeChanged = pyqtSignal()
    swapAutoStatusChanged = pyqtSignal()
    oldBoardSnChanged = pyqtSignal()
    lastExportBinChanged = pyqtSignal()
    newBoardSerialChanged = pyqtSignal()
    capabilitiesChanged = pyqtSignal()
    progressStepChanged = pyqtSignal()
    swapAutoPhaseChanged = pyqtSignal()
    workflowChanged = pyqtSignal()

    _AUTO_PHASES = [
        "idle", "sn_detect", "sn_confirm", "exporting",
        "wait_swap", "wait_new", "cloning", "done",
    ]
    _AUTO_LABELS = [
        "待命", "读 FRU", "核对 SN", "导出",
        "等换板", "等新板", "克隆", "完成",
    ]
    _MANUAL_LABELS = ["等待", "导出", "克隆", "完成"]
    _MANUAL_LABELS_EN = ["WAIT", "EXPORT", "CLONE", "DONE"]
    _AUTO_LABELS_EN = [
        "STBY", "READ", "CHECK", "EXPORT",
        "SWAP", "NEW", "CLONE", "DONE",
    ]

    def __init__(self, swap: SwapController, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._swap = swap
        for sig, name in (
            (self.step1DoneChanged, "step1DoneChanged"),
            (self.step2DoneChanged, "step2DoneChanged"),
            (self.swapModeChanged, "swapModeChanged"),
            (self.swapAutoStatusChanged, "swapAutoStatusChanged"),
            (self.oldBoardSnChanged, "oldBoardSnChanged"),
            (self.lastExportBinChanged, "lastExportBinChanged"),
            (self.newBoardSerialChanged, "newBoardSerialChanged"),
            (self.capabilitiesChanged, "capabilitiesChanged"),
            (self.progressStepChanged, "progressStepChanged"),
            (self.swapAutoPhaseChanged, "swapAutoPhaseChanged"),
        ):
            relay(swap, name, self, sig)
        # workflow properties change whenever swap state changes
        for sig in (self.swapModeChanged, self.swapAutoPhaseChanged,
                    self.swapAutoStatusChanged, self.progressStepChanged):
            sig.connect(self.workflowChanged.emit)

    # --- Workflow derived properties (single source of truth for QML) ---

    @pyqtProperty(int, notify=workflowChanged)
    def workflowPhaseIndex(self) -> int:
        if self.swapMode == "auto":
            try:
                return self._AUTO_PHASES.index(self.swapAutoPhase)
            except ValueError:
                return 0
        return self.progressStep

    @pyqtProperty(float, notify=workflowChanged)
    def workflowProgress(self) -> float:
        if self.swapMode == "auto":
            idx = self.workflowPhaseIndex
            return idx / max(1, len(self._AUTO_PHASES) - 1)
        return self.progressStep / 3.0

    @pyqtProperty(str, notify=workflowChanged)
    def workflowStatusLabel(self) -> str:
        if self.swapMode == "auto":
            if self.swapAutoStatus:
                return self.swapAutoStatus
            idx = self.workflowPhaseIndex
            return self._AUTO_LABELS[idx] if 0 <= idx < len(self._AUTO_LABELS) else "自动换板"
        step = self.progressStep
        return self._MANUAL_LABELS[min(step, len(self._MANUAL_LABELS) - 1)]

    @pyqtProperty(str, notify=workflowChanged)
    def workflowStatusLabelEn(self) -> str:
        if self.swapMode == "auto":
            if self.swapAutoStatus:
                return self._swap.swapAutoStatusEn
            idx = self.workflowPhaseIndex
            return self._AUTO_LABELS_EN[idx] if 0 <= idx < len(self._AUTO_LABELS_EN) else "AUTO SWAP"
        step = self.progressStep
        return self._MANUAL_LABELS_EN[min(step, len(self._MANUAL_LABELS_EN) - 1)]

    @pyqtProperty(bool, notify=workflowChanged)
    def workflowFlowActive(self) -> bool:
        if self.swapMode == "auto":
            return self.swapAutoPhase != "idle" and self.swapAutoPhase != "done"
        return self.progressStep > 0

    @pyqtProperty(int, notify=workflowChanged)
    def workflowPhaseCount(self) -> int:
        return len(self._AUTO_PHASES) if self.swapMode == "auto" else len(self._MANUAL_LABELS)

    @pyqtProperty(int, notify=workflowChanged)
    def workflowActiveStepCard(self) -> int:
        if self.swapMode == "auto":
            idx = self.workflowPhaseIndex
            if idx <= 3:
                return 0
            if idx >= 7:
                return -1
            return 1
        if self.progressStep <= 0:
            return 0
        if self.progressStep >= 3:
            return -1
        return 1 if self.progressStep >= 2 else 0

    @pyqtProperty(str, notify=swapModeChanged)
    def swapMode(self) -> str:
        return self._swap.swapMode

    @pyqtProperty(str, notify=swapAutoStatusChanged)
    def swapAutoStatus(self) -> str:
        return self._swap.swapAutoStatus

    @pyqtProperty(str, notify=oldBoardSnChanged)
    def oldBoardSn(self) -> str:
        return self._swap.oldBoardSn

    @pyqtSlot(str)
    def setOldBoardSn(self, sn: str) -> None:
        self._swap.setOldBoardSn(sn)

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canStep1(self) -> bool:
        return self._swap.canStep1

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canStep2(self) -> bool:
        return self._swap.canStep2

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canRollback(self) -> bool:
        return self._swap.canRollback

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canSwapReset(self) -> bool:
        return self._swap.canSwapReset

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def step2Locked(self) -> bool:
        return self._swap.step2Locked

    @pyqtProperty(bool, notify=step1DoneChanged)
    def step1Done(self) -> bool:
        return self._swap.step1Done

    @pyqtProperty(bool, notify=step2DoneChanged)
    def step2Done(self) -> bool:
        return self._swap.step2Done

    @pyqtProperty(str, notify=lastExportBinChanged)
    def lastExportBin(self) -> str:
        return self._swap.lastExportBin

    @pyqtProperty(str, notify=newBoardSerialChanged)
    def newBoardSerial(self) -> str:
        return self._swap.newBoardSerial

    @pyqtProperty(int, notify=progressStepChanged)
    def progressStep(self) -> int:
        return self._swap.progressStep

    @pyqtProperty(str, notify=swapAutoPhaseChanged)
    def swapAutoPhase(self) -> str:
        return self._swap.swapAutoPhase

    @pyqtSlot(str)
    def setSwapMode(self, mode: str) -> None:
        self._swap.setSwapMode(mode)

    @pyqtSlot()
    def doStep1(self) -> None:
        self._swap.doStep1()

    @pyqtSlot()
    def doStep2(self) -> None:
        self._swap.doStep2()

    @pyqtSlot()
    def doRollback(self) -> None:
        self._swap.doRollback()

    @pyqtSlot()
    def doSwapReset(self) -> None:
        self._swap.doSwapReset()
