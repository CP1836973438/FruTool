"""Terminal and log dock ViewModel."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.presentation.controller import TerminalController
from frutool.presentation.viewmodels._relay import relay


class TerminalViewModel(QObject):
    logDockOpenChanged = pyqtSignal()
    lastLogPlainChanged = pyqtSignal()
    lastLogLevelChanged = pyqtSignal()
    activeLogTabChanged = pyqtSignal()
    unreadCountsChanged = pyqtSignal()
    logActivityChanged = pyqtSignal()
    cmdModeChanged = pyqtSignal()
    cmdCredUseNewChanged = pyqtSignal()

    def __init__(self, terminal: TerminalController, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._terminal = terminal
        for sig, name in (
            (self.logDockOpenChanged, "logDockOpenChanged"),
            (self.lastLogPlainChanged, "lastLogPlainChanged"),
            (self.lastLogLevelChanged, "lastLogLevelChanged"),
            (self.activeLogTabChanged, "activeLogTabChanged"),
            (self.unreadCountsChanged, "unreadCountsChanged"),
            (self.logActivityChanged, "logActivityChanged"),
            (self.cmdModeChanged, "cmdModeChanged"),
            (self.cmdCredUseNewChanged, "cmdCredUseNewChanged"),
        ):
            relay(terminal, name, self, sig)

    @pyqtProperty(QObject, constant=True)
    def logModelProp(self) -> QObject:
        return self._terminal.log_model

    @pyqtProperty(bool, notify=logDockOpenChanged)
    def logDockOpen(self) -> bool:
        return self._terminal.logDockOpen

    @pyqtSlot(bool)
    def setLogDockOpen(self, open_: bool) -> None:
        self._terminal.setLogDockOpen(open_)

    @pyqtProperty(str, notify=lastLogPlainChanged)
    def lastLogPlain(self) -> str:
        return self._terminal.lastLogPlain

    @pyqtProperty(str, notify=lastLogLevelChanged)
    def lastLogLevel(self) -> str:
        return self._terminal.lastLogLevel

    @pyqtProperty(bool, notify=logActivityChanged)
    def logActivity(self) -> bool:
        return self._terminal.logActivity

    @pyqtProperty(int, notify=unreadCountsChanged)
    def unreadAll(self) -> int:
        return self._terminal.unreadAll

    @pyqtProperty(int, notify=unreadCountsChanged)
    def unreadDhcp(self) -> int:
        return self._terminal.unreadDhcp

    @pyqtProperty(int, notify=unreadCountsChanged)
    def unreadFru(self) -> int:
        return self._terminal.unreadFru

    @pyqtProperty(int, notify=unreadCountsChanged)
    def unreadTopo(self) -> int:
        return self._terminal.unreadTopo

    @pyqtProperty(bool, notify=unreadCountsChanged)
    def compactHasUnread(self) -> bool:
        return self._terminal.compactHasUnread

    @pyqtProperty(str, notify=activeLogTabChanged)
    def activeLogTab(self) -> str:
        return self._terminal.activeLogTab

    @pyqtSlot(str)
    def setActiveLogTab(self, tab: str) -> None:
        self._terminal.setActiveLogTab(tab)

    @pyqtSlot(str)
    def clearLogs(self, tab: str = "all") -> None:
        self._terminal.clearLogs(tab)

    @pyqtProperty(str, notify=cmdModeChanged)
    def cmdMode(self) -> str:
        return self._terminal.cmdMode

    @pyqtSlot(str)
    def setCmdMode(self, mode: str) -> None:
        self._terminal.setCmdMode(mode)

    @pyqtProperty(bool, notify=cmdCredUseNewChanged)
    def cmdCredUseNew(self) -> bool:
        return self._terminal.cmdCredUseNew

    @pyqtSlot(bool)
    def setCmdCredUseNew(self, use_new: bool) -> None:
        self._terminal.setCmdCredUseNew(use_new)

    @pyqtSlot(str, result=str)
    def completeTab(self, text: str) -> str:
        return self._terminal.completeTab(text)

    @pyqtSlot(str, result=str)
    def cmdHistoryUp(self, current: str) -> str:
        return self._terminal.cmdHistoryUp(current)

    @pyqtSlot(str, result=str)
    def cmdHistoryDown(self, current: str) -> str:
        return self._terminal.cmdHistoryDown(current)

    @pyqtSlot()
    def resetCmdLineBrowse(self) -> None:
        self._terminal.resetCmdLineBrowse()

    @pyqtSlot(str)
    def runManualCmd(self, cmd_str: str) -> None:
        self._terminal.runManualCmd(cmd_str)

    @pyqtSlot(result=bool)
    def interruptShellCmd(self) -> bool:
        return self._terminal.interruptShellCmd()
