"""Shared runtime context for domain controllers."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from PyQt6.QtCore import QThreadPool

from frutool.config import LogCallback
from frutool.presentation.models import FruFieldModel, LogLineModel, NetworkListModel, ThemeBridge
from frutool.presentation.services import (
    ConnCredentials,
    DialogService,
    LogService,
    ShellService,
    SwapAutoService,
    TerminalService,
)

if TYPE_CHECKING:
    from frutool.presentation.controller.application import ApplicationController


class ApplicationHost:
    """Non-Qt shared dependencies and cross-domain helpers."""

    def __init__(self) -> None:
        self.thread_pool = QThreadPool.globalInstance()
        self.log_model = LogLineModel()
        self.network_model = NetworkListModel()
        self.fru_field_model = FruFieldModel()
        self.theme_bridge = ThemeBridge()
        self.conn = ConnCredentials()
        self.log_service = LogService()
        self.dialog_service = DialogService()
        self.shell = ShellService()
        self.terminal = TerminalService()
        self.swap_auto: Optional[SwapAutoService] = None
        self.closing = False
        self.busy = False
        self._log_tab_stack: list[str] = []
        self._app: Optional[ApplicationController] = None

    @property
    def log_tab_override(self) -> Optional[str]:
        return self._log_tab_stack[-1] if self._log_tab_stack else None

    def push_log_tab(self, tab: str) -> None:
        self._log_tab_stack.append(tab)

    def pop_log_tab(self) -> None:
        if self._log_tab_stack:
            self._log_tab_stack.pop()

    def bind(self, app: ApplicationController) -> None:
        self._app = app
        parent = app
        self.log_model.setParent(parent)
        self.network_model.setParent(parent)
        self.fru_field_model.setParent(parent)
        self.theme_bridge.setParent(parent)

    @property
    def app(self) -> ApplicationController:
        assert self._app is not None
        return self._app

    def log(self, level: str, message: str) -> None:
        self.app.log(level, message)

    def run_worker(
        self,
        fn: Callable[[LogCallback], object],
        done: Callable[[object], None],
        log_tab: Optional[str] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.app.run_worker(fn, done, log_tab=log_tab, on_error=on_error)

    def set_busy(self, busy: bool) -> None:
        self.app.set_busy(busy)

    def refresh_capabilities(self) -> None:
        if self._app is not None:
            self._app.swap.refresh_capabilities()

    def request_dialog(self, payload: dict, callback: Optional[Callable[[bool], None]] = None) -> None:
        self.app.request_dialog(payload, callback)

    def request_info(self, title: str, message: str) -> None:
        self.app.request_info(title, message)

    def request_critical(self, title: str, message: str) -> None:
        self.app.request_critical(title, message)

    def request_warning(self, title: str, message: str) -> None:
        self.app.request_warning(title, message)

    def request_question(
        self,
        title: str,
        message: str,
        callback: Callable[[bool], None],
        *,
        default_no: bool = False,
    ) -> None:
        self.app.request_question(title, message, callback, default_no=default_no)
