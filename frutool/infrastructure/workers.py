"""Background worker threads."""
from __future__ import annotations

import threading
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from frutool.config import BMC_PING_INTERVAL_S, BMC_PING_TIMEOUT_MS, LogCallback
from frutool.domain.ipmi import probe_bmc_ping


class BMCProbeThread(threading.Thread):
    def __init__(
        self,
        bmc_state_cb: Callable[[bool], None],
        local_state_cb: Callable[[bool], None],
        bmc_ip_provider: Callable[[], str],
        local_ip_provider: Callable[[], str],
        link_up_provider: Callable[[], Optional[bool]],
    ):
        super().__init__(daemon=True)
        self.bmc_state_cb = bmc_state_cb
        self.local_state_cb = local_state_cb
        self.bmc_ip_provider = bmc_ip_provider
        self.local_ip_provider = local_ip_provider
        self.link_up_provider = link_up_provider
        self._stop_event = threading.Event()
        self._last_bmc_online: Optional[bool] = None
        self._last_local_online: Optional[bool] = None

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            try:
                local_ip = self.local_ip_provider()
                local_online = bool(local_ip) and probe_bmc_ping(local_ip, BMC_PING_TIMEOUT_MS)
                if local_online != self._last_local_online:
                    self._last_local_online = local_online
                    self.local_state_cb(local_online)

                link_up = self.link_up_provider()
                if link_up is False:
                    bmc_online = False
                else:
                    bmc_ip = self.bmc_ip_provider()
                    bmc_online = bool(bmc_ip) and probe_bmc_ping(bmc_ip, BMC_PING_TIMEOUT_MS)
                if bmc_online != self._last_bmc_online:
                    self._last_bmc_online = bmc_online
                    self.bmc_state_cb(bmc_online)
            except Exception:
                pass

            if self._stop_event.wait(BMC_PING_INTERVAL_S):
                break


class WorkerSignals(QObject):
    log = pyqtSignal(str, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)


class Worker(QRunnable):
    def __init__(self, fn: Callable[[LogCallback], object], *, owner: QObject):
        super().__init__()
        self.setAutoDelete(True)
        self.fn = fn
        self.result: object = None
        self.signals = WorkerSignals(owner)

    @pyqtSlot()
    def run(self):
        try:
            self.result = self.fn(self._emit_log)
            self.signals.finished.emit()
        except Exception as exc:
            try:
                self.signals.error.emit(str(exc))
            except RuntimeError:
                pass

    def _emit_log(self, level: str, message: str) -> None:
        self.signals.log.emit(level, message)


LOG_MAX_BLOCKS = 800
