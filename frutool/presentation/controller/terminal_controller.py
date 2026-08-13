"""Terminal controller — log dock, command line, shell/IPMI execution."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.config import LogCallback
from frutool.presentation.controller.base import ApplicationHost
from frutool.presentation.services import PreparedLogLine, is_shell_ipmi_command, parse_ipmi_args, run_ipmi_command

if TYPE_CHECKING:
    from frutool.presentation.controller.conn_controller import ConnController

_LOG_TABS = ("all", "dhcp", "fru", "topo")
_ACTIVITY_MS = 2000


class TerminalController(QObject):
    """Log dock visibility, active tab, and manual shell/IPMI commands."""

    logDockOpenChanged = pyqtSignal()
    lastLogPlainChanged = pyqtSignal()
    lastLogLevelChanged = pyqtSignal()
    activeLogTabChanged = pyqtSignal()
    unreadCountsChanged = pyqtSignal()
    logActivityChanged = pyqtSignal()
    cmdModeChanged = pyqtSignal()
    cmdCredUseNewChanged = pyqtSignal()
    shellCmdRunningChanged = pyqtSignal()

    def __init__(
        self,
        host: ApplicationHost,
        conn: ConnController,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._host = host
        self._conn = conn
        self._log_dock_open = False
        self._last_log_plain = "日志：—"
        self._last_log_level = "info"
        self._active_log_tab = "all"
        self._cmd_mode = "IPMI模式"
        self._cmd_cred_use_new = True
        self._unread = {tab: 0 for tab in _LOG_TABS}
        self._log_activity = False
        self._activity_timer = QTimer(self)
        self._activity_timer.setSingleShot(True)
        self._activity_timer.timeout.connect(self._clear_log_activity)

    @property
    def log_model(self):
        return self._host.log_model

    # --- Log dock ---

    @pyqtProperty(bool, notify=logDockOpenChanged)
    def logDockOpen(self) -> bool:
        return self._log_dock_open

    @pyqtSlot(bool)
    def setLogDockOpen(self, open_: bool) -> None:
        if open_ == self._log_dock_open:
            return
        self._log_dock_open = open_
        if open_:
            self._clear_all_unread()
        self.logDockOpenChanged.emit()

    @pyqtProperty(str, notify=lastLogPlainChanged)
    def lastLogPlain(self) -> str:
        return self._last_log_plain

    @pyqtProperty(str, notify=lastLogLevelChanged)
    def lastLogLevel(self) -> str:
        return self._last_log_level

    @pyqtProperty(bool, notify=logActivityChanged)
    def logActivity(self) -> bool:
        return self._log_activity

    @pyqtProperty(int, notify=unreadCountsChanged)
    def unreadAll(self) -> int:
        return self._unread["all"]

    @pyqtProperty(int, notify=unreadCountsChanged)
    def unreadDhcp(self) -> int:
        return self._unread["dhcp"]

    @pyqtProperty(int, notify=unreadCountsChanged)
    def unreadFru(self) -> int:
        return self._unread["fru"]

    @pyqtProperty(int, notify=unreadCountsChanged)
    def unreadTopo(self) -> int:
        return self._unread["topo"]

    @pyqtProperty(bool, notify=unreadCountsChanged)
    def compactHasUnread(self) -> bool:
        return not self._log_dock_open and any(self._unread[tab] > 0 for tab in _LOG_TABS)

    def append_log_prepared(self, level: str, prepared: PreparedLogLine) -> None:
        self._last_log_plain = prepared.last_plain
        self.lastLogPlainChanged.emit()
        if level != self._last_log_level:
            self._last_log_level = level
            self.lastLogLevelChanged.emit()
        self._mark_log_activity()
        for tab in prepared.tabs:
            if tab not in self._unread:
                continue
            if self._log_dock_open and tab == self._active_log_tab:
                continue
            self._unread[tab] += 1
        self.unreadCountsChanged.emit()

    @pyqtProperty(str, notify=activeLogTabChanged)
    def activeLogTab(self) -> str:
        return self._active_log_tab

    @pyqtSlot(str)
    def setActiveLogTab(self, tab: str) -> None:
        if tab in self._unread and self._unread[tab] != 0:
            self._unread[tab] = 0
            self.unreadCountsChanged.emit()
        if tab == self._active_log_tab:
            return
        self._active_log_tab = tab
        self._host.log_model.tabFilter = tab
        self.activeLogTabChanged.emit()

    @pyqtSlot(str)
    def clearLogs(self, tab: str = "all") -> None:
        key = tab if tab else self._active_log_tab
        self._host.log_model.clearTab(key)
        if key in self._unread:
            self._unread[key] = 0
            self.unreadCountsChanged.emit()

    def _clear_all_unread(self) -> None:
        changed = False
        for tab in _LOG_TABS:
            if self._unread[tab] != 0:
                self._unread[tab] = 0
                changed = True
        if changed:
            self.unreadCountsChanged.emit()

    def _mark_log_activity(self) -> None:
        if not self._log_activity:
            self._log_activity = True
            self.logActivityChanged.emit()
        self._activity_timer.start(_ACTIVITY_MS)

    def _clear_log_activity(self) -> None:
        if not self._log_activity:
            return
        self._log_activity = False
        self.logActivityChanged.emit()

    # --- Command mode ---

    @pyqtProperty(str, notify=cmdModeChanged)
    def cmdMode(self) -> str:
        return self._cmd_mode

    @pyqtSlot(str)
    def setCmdMode(self, mode: str) -> None:
        if mode == self._cmd_mode:
            return
        self._cmd_mode = mode
        self.cmdModeChanged.emit()

    @pyqtProperty(bool, notify=cmdCredUseNewChanged)
    def cmdCredUseNew(self) -> bool:
        return self._cmd_cred_use_new

    @pyqtSlot(bool)
    def setCmdCredUseNew(self, use_new: bool) -> None:
        if use_new == self._cmd_cred_use_new:
            return
        self._cmd_cred_use_new = use_new
        self.cmdCredUseNewChanged.emit()

    @pyqtProperty(bool, notify=shellCmdRunningChanged)
    def shellCmdRunning(self) -> bool:
        return self._host.shell.running

    @pyqtSlot(str, result=str)
    def completeTab(self, text: str) -> str:
        return self._host.terminal.complete_tab(self._cmd_mode, text)

    @pyqtSlot(str, result=str)
    def cmdHistoryUp(self, current: str) -> str:
        return self._host.terminal.history_up(current)

    @pyqtSlot(str, result=str)
    def cmdHistoryDown(self, current: str) -> str:
        return self._host.terminal.history_down(current)

    @pyqtSlot()
    def resetCmdLineBrowse(self) -> None:
        self._host.terminal.reset_browse()

    def _manual_cmd_log_tab(self, cmd_str: str) -> str:
        if self._cmd_mode == "IPMI模式":
            return "fru"
        if is_shell_ipmi_command(cmd_str):
            return "fru"
        return "all"

    @pyqtSlot(str)
    def runManualCmd(self, cmd_str: str) -> None:
        cmd_str = cmd_str.strip()
        if not cmd_str:
            return
        log_tab = self._manual_cmd_log_tab(cmd_str)
        if self._cmd_mode == "IPMI模式":
            extra_args, err = parse_ipmi_args(cmd_str)
            if err:
                title, message, kind = err
                getattr(self._host, f"request_{kind}")(title, message)
                return
            user, pwd = self._conn.credentials(self._cmd_cred_use_new)
            bmc_ip = self._conn.bmc_ip

            def job(log: LogCallback):
                return run_ipmi_command(cmd_str, user, pwd, bmc_ip, log)

            self._host.terminal.record_command(cmd_str)
            self._host.run_worker(job, lambda _result: None, log_tab=log_tab)
        else:
            if self._host.shell.running:
                self._host.log("warning", "已有命令在运行，请 Ctrl+C 终止后再执行")
                return
            self._host.shell.begin()
            self.shellCmdRunningChanged.emit()

            def job(log: LogCallback):
                return self._host.shell.run_job(cmd_str, log)

            self._host.terminal.record_command(cmd_str)
            self._host.run_worker(job, self._on_shell_cmd_done, log_tab=log_tab)

    def _on_shell_cmd_done(self, _result: object) -> None:
        self._host.shell.finish()
        self.shellCmdRunningChanged.emit()

    @pyqtSlot(result=bool)
    def interruptShellCmd(self) -> bool:
        interrupted = self._host.shell.interrupt()
        if interrupted:
            self.shellCmdRunningChanged.emit()
        return interrupted

    def on_worker_error(self) -> None:
        """Called by ApplicationController when a background worker fails."""
        self._host.shell.finish()
        self.shellCmdRunningChanged.emit()
