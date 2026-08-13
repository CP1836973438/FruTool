"""ApplicationController — composes domain controllers and shared Qt infrastructure."""
from __future__ import annotations

import uuid
from typing import Callable, Optional

from PyQt6.QtCore import QObject, Qt, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.config import LogCallback
from frutool.infrastructure.workers import Worker
from frutool.presentation.controller.base import ApplicationHost
from frutool.presentation.controller.chrome_controller import ChromeController
from frutool.presentation.controller.conn_controller import ConnController
from frutool.presentation.controller.ops_controller import OpsController
from frutool.presentation.controller.swap_controller import SwapController
from frutool.presentation.controller.terminal_controller import TerminalController
from frutool.presentation.services import prepare_log_line


class ApplicationController(QObject):
    """Root orchestrator: logging, workers, dialogs, lifecycle; domain logic in sub-controllers."""

    dialogRequested = pyqtSignal(str)
    aboutRequested = pyqtSignal()
    quitRequested = pyqtSignal()
    busyChanged = pyqtSignal()

    _log_signal = pyqtSignal(str, str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.host = ApplicationHost()
        self.host.bind(self)

        self.conn = ConnController(self.host, self)
        self.swap = SwapController(self.host, self.conn, self)
        self.ops = OpsController(self.host, self.conn, self.swap, self)
        self.terminal = TerminalController(self.host, self.conn, self)
        self.chrome = ChromeController(self.host, self.swap, self)
        self.ops.bind_chrome(self.chrome)

        self.conn.bmcOnlineChanged.connect(self.swap.on_bmc_online_changed)
        self.conn.bmcOnlineChanged.connect(self.ops.on_bmc_online_changed)
        self.chrome.aboutRequested.connect(self.aboutRequested.emit)

        self._workers: list[Worker] = []
        self._log_signal.connect(self._append_log, Qt.ConnectionType.QueuedConnection)

        self._init_session_log()
        self.conn.startup()
        self.swap.sync_step1_from_backup()
        self.swap.restore_session()

    # --- Models (legacy accessors) ---

    @property
    def logModel(self):
        return self.host.log_model

    @property
    def networkModel(self):
        return self.host.network_model

    @property
    def fruFieldModel(self):
        return self.host.fru_field_model

    @property
    def themeBridge(self):
        return self.host.theme_bridge

    @pyqtProperty(QObject, constant=True)
    def logModelProp(self) -> QObject:
        return self.host.log_model

    @pyqtProperty(QObject, constant=True)
    def networkModelProp(self) -> QObject:
        return self.host.network_model

    @pyqtProperty(QObject, constant=True)
    def fruFieldModelProp(self) -> QObject:
        return self.host.fru_field_model

    @pyqtProperty(QObject, constant=True)
    def themeBridgeProp(self) -> QObject:
        return self.host.theme_bridge

    @pyqtProperty(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self.host.busy

    # --- Dialog API ---

    def request_dialog(self, payload: dict, callback: Optional[Callable[[bool], None]] = None) -> None:
        self.dialogRequested.emit(self.host.dialog_service.prepare_payload(payload, callback))

    def request_info(self, title: str, message: str) -> None:
        self.request_dialog({"type": "info", "title": title, "message": message})

    def request_critical(self, title: str, message: str) -> None:
        self.request_dialog({"type": "critical", "title": title, "message": message})

    def request_warning(self, title: str, message: str) -> None:
        self.request_dialog({"type": "warning", "title": title, "message": message})

    def request_question(
        self,
        title: str,
        message: str,
        callback: Callable[[bool], None],
        *,
        default_no: bool = False,
    ) -> None:
        self.request_dialog(
            {
                "type": "question",
                "title": title,
                "message": message,
                "defaultNo": default_no,
            },
            callback,
        )

    @pyqtSlot(str, bool)
    def dialogResponse(self, dialog_id: str, accepted: bool) -> None:
        self.host.dialog_service.respond(dialog_id, accepted)

    @pyqtSlot(str, bool)
    def snConfirmResponse(self, dialog_id: str, accepted: bool) -> None:
        self.swap.sn_confirm_response(dialog_id, accepted)

    # --- Shared infrastructure ---

    def log(self, level: str, message: str) -> None:
        if self.host.closing:
            return
        self._log_signal.emit(level, message)

    def _append_log(self, level: str, message: str) -> None:
        prepared = prepare_log_line(level, message, tab_override=self.host.log_tab_override)
        for key in prepared.tabs:
            self.host.log_model.append(level, message, prepared.short_ts, key)
        self.host.log_service.write_line(prepared.file_line)
        self.terminal.append_log_prepared(level, prepared)
        if prepared.mac:
            self.conn.set_mac_address(prepared.mac)

    def _init_session_log(self) -> None:
        path = self.host.log_service.init_session()
        self.log("info", f"操作日志已写入 {path}")

    def set_busy(self, busy: bool) -> None:
        if busy == self.host.busy:
            return
        self.host.busy = busy
        self.busyChanged.emit()
        self.swap.refresh_capabilities()

    def run_worker(
        self,
        fn: Callable[[LogCallback], object],
        done: Callable[[object], None],
        log_tab: Optional[str] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        if log_tab is not None:
            self.host.push_log_tab(log_tab)

        def _clear_override() -> None:
            if log_tab is not None:
                self.host.pop_log_tab()

        worker = Worker(fn, owner=self)
        self._workers.append(worker)

        def _done() -> None:
            result = worker.result
            self._release_worker(worker)
            _clear_override()
            if not self.host.closing:
                done(result)

        def _error(message: str) -> None:
            self._release_worker(worker)
            _clear_override()
            if self.host.closing:
                return
            if on_error is not None:
                on_error(message)
            else:
                self._on_worker_error(message)

        worker.signals.log.connect(self.log, Qt.ConnectionType.QueuedConnection)
        worker.signals.finished.connect(_done, Qt.ConnectionType.QueuedConnection)
        worker.signals.error.connect(_error, Qt.ConnectionType.QueuedConnection)
        self.host.thread_pool.start(worker)

    def _release_worker(self, worker: Worker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)

    def _on_worker_error(self, message: str) -> None:
        self.terminal.on_worker_error()
        self.set_busy(False)
        self.log("error", f"后台任务错误: {message}")
        self.request_critical("后台任务错误", message)

    # --- Lifecycle ---

    @pyqtSlot()
    def begin_shutdown(self) -> None:
        """Mark closing and persist session; keep QML bindings alive until window closes."""
        if self.host.closing:
            return
        self.host.closing = True
        self.swap.persist_session()

    def finalize_shutdown(self) -> None:
        """Stop background work after the QML window has closed."""
        if getattr(self, "_finalized", False):
            return
        self._finalized = True
        if not self.host.closing:
            self.begin_shutdown()
        self.swap.shutdown_swap()
        self.conn.shutdown()
        self.chrome.shutdown()
        self.host.thread_pool.waitForDone(5000)
        self.host.log_service.close()

    @pyqtSlot()
    def shutdown(self) -> None:
        """Immediate shutdown (tests/tools); GUI exit uses begin + finalize."""
        self.begin_shutdown()
        self.finalize_shutdown()
