"""Connection page ViewModel."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.presentation.controller import ConnController
from frutool.presentation.viewmodels._relay import relay


class ConnViewModel(QObject):
    connFieldChanged = pyqtSignal()
    showPasswordsChanged = pyqtSignal()
    networkSummaryChanged = pyqtSignal()
    networkRefreshingChanged = pyqtSignal()
    selectedNetworkIndexChanged = pyqtSignal()
    bmcOnlineChanged = pyqtSignal(bool)
    localOnlineChanged = pyqtSignal()
    bmcIpChanged = pyqtSignal()
    localIpChanged = pyqtSignal()
    macAddressChanged = pyqtSignal()

    def __init__(self, conn: ConnController, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._conn = conn
        for sig, name in (
            (self.connFieldChanged, "connFieldChanged"),
            (self.showPasswordsChanged, "showPasswordsChanged"),
            (self.networkSummaryChanged, "networkSummaryChanged"),
            (self.networkRefreshingChanged, "networkRefreshingChanged"),
            (self.selectedNetworkIndexChanged, "selectedNetworkIndexChanged"),
            (self.bmcOnlineChanged, "bmcOnlineChanged"),
            (self.localOnlineChanged, "localOnlineChanged"),
            (self.bmcIpChanged, "bmcIpChanged"),
            (self.localIpChanged, "localIpChanged"),
            (self.macAddressChanged, "macAddressChanged"),
        ):
            relay(conn, name, self, sig)

    @pyqtProperty(QObject, constant=True)
    def networkModelProp(self) -> QObject:
        return self._conn.network_model

    @pyqtProperty(str, notify=connFieldChanged)
    def oldBoardUser(self) -> str:
        return self._conn.oldBoardUser

    @pyqtProperty(str, notify=connFieldChanged)
    def oldBoardPassword(self) -> str:
        return self._conn.oldBoardPassword

    @pyqtProperty(str, notify=connFieldChanged)
    def newBoardUser(self) -> str:
        return self._conn.newBoardUser

    @pyqtProperty(str, notify=connFieldChanged)
    def newBoardPassword(self) -> str:
        return self._conn.newBoardPassword

    @pyqtSlot(str, str)
    def setConnField(self, key: str, value: str) -> None:
        self._conn.setConnField(key, value)

    @pyqtProperty(bool, notify=showPasswordsChanged)
    def showPasswords(self) -> bool:
        return self._conn.showPasswords

    @pyqtSlot(bool)
    def setShowPasswords(self, show: bool) -> None:
        self._conn.setShowPasswords(show)

    @pyqtProperty(str, notify=networkSummaryChanged)
    def networkSummary(self) -> str:
        return self._conn.networkSummary

    @pyqtProperty(str, notify=networkSummaryChanged)
    def networkIpWarning(self) -> str:
        return self._conn.networkIpWarning

    @pyqtProperty(bool, notify=networkRefreshingChanged)
    def networkRefreshing(self) -> bool:
        return self._conn.networkRefreshing

    @pyqtProperty(int, notify=selectedNetworkIndexChanged)
    def selectedNetworkIndex(self) -> int:
        return self._conn.selectedNetworkIndex

    @pyqtSlot(int)
    def setSelectedNetworkIndex(self, index: int) -> None:
        self._conn.setSelectedNetworkIndex(index)

    @pyqtSlot(bool)
    def refreshNetworks(self, initial: bool = False) -> None:
        self._conn.refreshNetworks(initial)

    @pyqtProperty(bool, notify=bmcOnlineChanged)
    def bmcOnline(self) -> bool:
        return self._conn.bmcOnline

    @pyqtProperty(bool, notify=localOnlineChanged)
    def localOnline(self) -> bool:
        return self._conn.localOnline

    @pyqtProperty(str, notify=bmcIpChanged)
    def bmcIp(self) -> str:
        return self._conn.bmcIp

    @pyqtProperty(str, notify=localIpChanged)
    def localIp(self) -> str:
        return self._conn.localIp

    @pyqtProperty(str, notify=macAddressChanged)
    def macAddress(self) -> str:
        return self._conn.macAddress

    @pyqtSlot()
    def openBmcWeb(self) -> None:
        self._conn.openBmcWeb()
