"""Connection controller — credentials UI + network facade."""
from __future__ import annotations

from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication

from frutool.config import LogCallback
from frutool.domain.ipmi import parse_board_serial, probe_fru_list
from frutool.presentation.controller.base import ApplicationHost
from frutool.presentation.controller.network_controller import NetworkController


class ConnController(QObject):
    """Credential fields and network reachability for the connection page."""

    connFieldChanged = pyqtSignal(str)
    showPasswordsChanged = pyqtSignal()
    networkSummaryChanged = pyqtSignal()
    networkRefreshingChanged = pyqtSignal()
    selectedNetworkIndexChanged = pyqtSignal()
    bmcOnlineChanged = pyqtSignal(bool)
    localOnlineChanged = pyqtSignal()
    bmcIpChanged = pyqtSignal()
    localIpChanged = pyqtSignal()
    macAddressChanged = pyqtSignal()

    def __init__(self, host: ApplicationHost, parent: QObject) -> None:
        super().__init__(parent)
        self._host = host
        self._show_passwords = False
        self._mac_address = ""
        self.network = NetworkController(host, self)

        for sig, name in (
            (self.networkSummaryChanged, "networkSummaryChanged"),
            (self.networkRefreshingChanged, "networkRefreshingChanged"),
            (self.selectedNetworkIndexChanged, "selectedNetworkIndexChanged"),
            (self.bmcOnlineChanged, "bmcOnlineChanged"),
            (self.localOnlineChanged, "localOnlineChanged"),
            (self.bmcIpChanged, "bmcIpChanged"),
            (self.localIpChanged, "localIpChanged"),
        ):
            getattr(self.network, name).connect(sig.emit)

    @property
    def network_model(self):
        return self.network.network_model

    @property
    def network_config(self):
        return self.network.network_config

    def startup(self) -> None:
        self.network.startup()

    def shutdown(self) -> None:
        self.network.shutdown()

    def credentials(self, use_new: bool) -> tuple[str, str]:
        return self._host.conn.for_board(use_new)

    @property
    def bmc_ip(self) -> str:
        return self.network.bmc_ip

    def apply_bmc_state_from_result(self, result: object) -> None:
        self.network.apply_bmc_state_from_result(result)

    def set_mac_address(self, mac: str) -> None:
        if mac == self._mac_address:
            return
        self._mac_address = mac
        self.macAddressChanged.emit()

    # --- Network delegation ---

    @pyqtProperty(bool, notify=bmcOnlineChanged)
    def bmcOnline(self) -> bool:
        return self.network.bmcOnline

    @pyqtProperty(bool, notify=localOnlineChanged)
    def localOnline(self) -> bool:
        return self.network.localOnline

    @pyqtProperty(str, notify=networkSummaryChanged)
    def networkSummary(self) -> str:
        return self.network.networkSummary

    @pyqtProperty(str, notify=networkSummaryChanged)
    def networkIpWarning(self) -> str:
        return self.network.networkIpWarning

    @pyqtProperty(bool, notify=networkRefreshingChanged)
    def networkRefreshing(self) -> bool:
        return self.network.networkRefreshing

    @pyqtProperty(int, notify=selectedNetworkIndexChanged)
    def selectedNetworkIndex(self) -> int:
        return self.network.selectedNetworkIndex

    @pyqtSlot(int)
    def setSelectedNetworkIndex(self, index: int) -> None:
        self.network.setSelectedNetworkIndex(index)

    @pyqtProperty(str, notify=bmcIpChanged)
    def bmcIp(self) -> str:
        return self.network.bmcIp

    @pyqtProperty(str, notify=localIpChanged)
    def localIp(self) -> str:
        return self.network.localIp

    @pyqtSlot(bool)
    def refreshNetworks(self, initial: bool = False) -> None:
        self.network.refreshNetworks(initial)

    @pyqtSlot()
    def openBmcWeb(self) -> None:
        if not self.network.bmcOnline:
            return
        ip = self.network_config.bmc_ip
        if not ip:
            return
        url = QUrl(f"http://{ip}")
        QDesktopServices.openUrl(url)

        old_user, old_pwd = self._host.conn.for_board(False)
        new_user, new_pwd = self._host.conn.for_board(True)
        bmc_ip = ip

        def probe_job(log_cb: LogCallback):
            ok, out = probe_fru_list(old_user, old_pwd, bmc_ip)
            if ok and parse_board_serial(out):
                return {"board": "old", "password": old_pwd}
            ok, out = probe_fru_list(new_user, new_pwd, bmc_ip)
            if ok and parse_board_serial(out):
                return {"board": "new", "password": new_pwd}
            return {"board": None, "password": None}

        def probe_done(result: object) -> None:
            if isinstance(result, dict) and result.get("password"):
                QApplication.clipboard().setText(result["password"])
                label = "旧板" if result["board"] == "old" else "新板"
                self._host.log("success", f"已自动复制{label}密码到剪贴板")
            else:
                self._host.log("warning", "无法通过 IPMI 判断板型，未自动复制密码")

        self._host.run_worker(probe_job, probe_done)

    # --- Credentials ---

    @pyqtProperty(str, notify=connFieldChanged)
    def oldBoardUser(self) -> str:
        return self._host.conn.old_user

    @pyqtProperty(str, notify=connFieldChanged)
    def oldBoardPassword(self) -> str:
        return self._host.conn.old_password

    @pyqtProperty(str, notify=connFieldChanged)
    def newBoardUser(self) -> str:
        return self._host.conn.new_user

    @pyqtProperty(str, notify=connFieldChanged)
    def newBoardPassword(self) -> str:
        return self._host.conn.new_password

    @pyqtSlot(str, str)
    def setConnField(self, key: str, value: str) -> None:
        field = self._host.conn.set(key, value)
        if field:
            self.connFieldChanged.emit(field)

    @pyqtProperty(bool, notify=showPasswordsChanged)
    def showPasswords(self) -> bool:
        return self._show_passwords

    @pyqtSlot(bool)
    def setShowPasswords(self, show: bool) -> None:
        if show == self._show_passwords:
            return
        self._show_passwords = show
        self.showPasswordsChanged.emit()

    @pyqtProperty(str, notify=macAddressChanged)
    def macAddress(self) -> str:
        return self._mac_address
