"""Chrome shell ViewModel (navigation, theme, about)."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.presentation.controller import ApplicationController, ChromeController
from frutool.presentation.viewmodels._relay import relay


class ChromeViewModel(QObject):
    currentPageChanged = pyqtSignal()
    themeModeChanged = pyqtSignal()
    quitRequested = pyqtSignal()

    def __init__(self, chrome: ChromeController, ctrl: ApplicationController, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._chrome = chrome
        self._ctrl = ctrl
        relay(chrome, "currentPageChanged", self, self.currentPageChanged)
        relay(chrome, "themeModeChanged", self, self.themeModeChanged)
        ctrl.quitRequested.connect(self.quitRequested.emit)

    @pyqtProperty(str, notify=currentPageChanged)
    def currentPage(self) -> str:
        return self._chrome.currentPage

    @pyqtSlot(str)
    def showPage(self, key: str) -> None:
        self._chrome.showPage(key)

    @pyqtProperty(str, notify=themeModeChanged)
    def themeMode(self) -> str:
        return self._chrome.themeMode

    @pyqtSlot(str)
    def setThemeMode(self, mode: str) -> None:
        self._chrome.setThemeMode(mode)

    @pyqtProperty(str, constant=True)
    def versionLabel(self) -> str:
        return self._chrome.versionLabel

    @pyqtProperty(str, constant=True)
    def appProductName(self) -> str:
        return self._chrome.appProductName

    @pyqtProperty(str, constant=True)
    def appDescription(self) -> str:
        return self._chrome.appDescription

    @pyqtProperty(str, constant=True)
    def appVersion(self) -> str:
        return self._chrome.appVersion

    @pyqtProperty(str, constant=True)
    def appCompany(self) -> str:
        return self._chrome.appCompany

    @pyqtProperty(str, constant=True)
    def appCopyright(self) -> str:
        return self._chrome.appCopyright

    @pyqtSlot()
    def showAbout(self) -> None:
        self._chrome.showAbout()

    @pyqtSlot(result=bool)
    def requestShutdown(self) -> bool:
        return self._chrome.requestShutdown()

    @pyqtProperty(QObject, constant=True)
    def themeBridgeProp(self) -> QObject:
        return self._chrome.theme_bridge
