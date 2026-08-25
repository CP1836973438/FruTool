"""Chrome controller — theme, navigation, about, shutdown."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.config import (
    APP_COMPANY,
    APP_CONTACT_EMAIL,
    APP_COPYRIGHT,
    APP_DESCRIPTION,
    APP_PRODUCT_NAME,
    APP_VERSION,
    APP_VERSION_LABEL,
)
from frutool.presentation.controller.base import ApplicationHost
from frutool.theme.tokens import resolve_theme_key

if TYPE_CHECKING:
    from frutool.presentation.controller.swap_controller import SwapController


class ChromeController(QObject):
    """Application chrome: theme, page navigation, about dialog, shutdown."""

    themeModeChanged = pyqtSignal()
    themeKeyChanged = pyqtSignal()
    currentPageChanged = pyqtSignal()
    aboutRequested = pyqtSignal()

    def __init__(
        self,
        host: ApplicationHost,
        swap: SwapController,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._host = host
        self._swap = swap
        self._theme_mode = "auto"
        self._theme_key = "dark"
        self._last_system_light: Optional[bool] = None
        self._current_page = "conn"

        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self._check_system_theme)

        self._apply_theme()
        self.theme_timer.start(2000)

    @property
    def theme_bridge(self):
        return self._host.theme_bridge

    # --- Theme ---

    @pyqtProperty(str, notify=themeModeChanged)
    def themeMode(self) -> str:
        return self._theme_mode

    @pyqtSlot(str)
    def setThemeMode(self, mode: str) -> None:
        if mode not in ("auto", "dark", "light") or mode == self._theme_mode:
            return
        self._theme_mode = mode
        self.themeModeChanged.emit()
        self._apply_theme()

    @pyqtProperty(str, notify=themeKeyChanged)
    def themeKey(self) -> str:
        return self._theme_key

    def _resolve_theme_key(self) -> str:
        key, light = resolve_theme_key(self._theme_mode, self._last_system_light)
        self._last_system_light = light
        return key

    def _check_system_theme(self) -> None:
        if self._theme_mode != "auto":
            return
        _key, light = resolve_theme_key(self._theme_mode, self._last_system_light)
        if light != self._last_system_light:
            self._apply_theme()

    def _apply_theme(self) -> None:
        key = self._resolve_theme_key()
        if key == self._theme_key:
            return
        self._theme_key = key
        self.themeKeyChanged.emit()
        self._host.theme_bridge.setThemeKey(key)
        self._host.log_model.setThemeKey(key)
        self._swap.progressStepChanged.emit()

    def shutdown(self) -> None:
        self.theme_timer.stop()

    # --- Navigation ---

    @pyqtProperty(str, notify=currentPageChanged)
    def currentPage(self) -> str:
        return self._current_page

    @pyqtSlot(str)
    def showPage(self, key: str) -> None:
        if key == self._current_page:
            return
        self._current_page = key
        self.currentPageChanged.emit()

    # --- App metadata ---

    @pyqtProperty(str, constant=True)
    def versionLabel(self) -> str:
        return APP_VERSION_LABEL

    @pyqtProperty(str, constant=True)
    def appProductName(self) -> str:
        return APP_PRODUCT_NAME

    @pyqtProperty(str, constant=True)
    def appDescription(self) -> str:
        return APP_DESCRIPTION

    @pyqtProperty(str, constant=True)
    def appVersion(self) -> str:
        return APP_VERSION

    @pyqtProperty(str, constant=True)
    def appCompany(self) -> str:
        return APP_COMPANY

    @pyqtProperty(str, constant=True)
    def appCopyright(self) -> str:
        return APP_COPYRIGHT

    @pyqtProperty(str, constant=True)
    def appContactEmail(self) -> str:
        return APP_CONTACT_EMAIL

    @pyqtSlot()
    def showAbout(self) -> None:
        self.aboutRequested.emit()

    # --- Shutdown ---

    @pyqtSlot(result=bool)
    def requestShutdown(self) -> bool:
        """Returns True if shutdown may proceed immediately."""
        return self.request_shutdown()

    def request_shutdown(self) -> bool:
        """Always returns False — exit via quitRequested + QApplication.quit(), not window.close()."""
        if self._host.closing:
            self._host.app.quitRequested.emit()
            return False
        if not self._host.busy:
            self._host.app.begin_shutdown()
            self._host.app.quitRequested.emit()
            return False
        dialog_id = str(uuid.uuid4())

        def on_answer(ok: bool):
            if ok:
                self._host.app.begin_shutdown()
                self._host.app.quitRequested.emit()

        self._host.request_dialog(
            {
                "type": "question",
                "id": dialog_id,
                "title": "正在刷写硬件",
                "message": (
                    "正在向底层硬件刷写关键数据（FRU / 拓扑），此时强行关闭可能导致主板 EEPROM 损坏。\n\n"
                    "确认要强制退出吗？"
                ),
                "defaultNo": True,
            },
            on_answer,
        )
        return False
