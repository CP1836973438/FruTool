"""Network runtime — NIC enumeration, link poll, DHCP, BMC/local probe."""
from __future__ import annotations

import os
import time
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.config import (
    BMC_PING_TIMEOUT_MS,
    BMC_PROBE_JOIN_TIMEOUT_S,
    LINK_POLL_INTERVAL_MS,
    LogCallback,
    NETWORK_CHANGE_DEBOUNCE_MS,
    NETWORK_STARTUP_DELAY_MS,
    NETWORK_STARTUP_MAX_ATTEMPTS,
    NETWORK_STARTUP_RETRY_MS,
)
from frutool.domain.dhcp import DHCPServer
from frutool.infrastructure.network import (
    NetworkChoice,
    NetworkConfig,
    _cleanup_legacy_nic_ip_backup,
    _preferred_bmc_nic_index,
    make_network_config,
)
from frutool.infrastructure.workers import BMCProbeThread
from frutool.presentation.controller.base import ApplicationHost
from frutool.presentation.services import (
    config_after_choice,
    describe_link_transition,
    format_network_ip_warning,
    network_refresh_log_message,
    network_choices_usable,
    normalize_network_choices,
    restart_dhcp_server,
    run_enumerate_networks_job,
    run_link_poll_job,
    run_local_ip_probe_job,
    should_run_dhcp,
)


class NetworkController(QObject):
    """Network interface selection, link monitoring, DHCP, and BMC/local reachability."""

    networkSummaryChanged = pyqtSignal()
    networkRefreshingChanged = pyqtSignal()
    selectedNetworkIndexChanged = pyqtSignal()
    bmcOnlineChanged = pyqtSignal(bool)
    localOnlineChanged = pyqtSignal()
    bmcIpChanged = pyqtSignal()
    localIpChanged = pyqtSignal()

    def __init__(self, host: ApplicationHost, parent: QObject) -> None:
        super().__init__(parent)
        self._host = host
        self.network_config: NetworkConfig = make_network_config(None)
        self.network_choices: list[NetworkChoice] = []
        self._dhcp_server: Optional[DHCPServer] = None
        self._dhcp_sync_key: Optional[tuple] = None
        self._bmc_probe_thread: Optional[BMCProbeThread] = None
        self._network_refresh_running = False
        self._selected_network_index = 0
        self._bmc_online = False
        self._local_online = False
        self._local_probe_in_flight = False
        self._link_up: Optional[bool] = None
        self._link_poll_in_flight = False
        self._network_summary = ""
        self._network_ip_warning = ""
        self._grace_until: float = 0.0
        self._startup_retry_active = False
        self._startup_network_attempt = 0

        self._network_debounce_timer = QTimer(self)
        self._network_debounce_timer.setSingleShot(True)
        self._network_debounce_timer.timeout.connect(self._apply_network_changed)

        self._startup_network_timer = QTimer(self)
        self._startup_network_timer.setSingleShot(True)
        self._startup_network_timer.timeout.connect(self._run_startup_network_refresh)

        self.link_timer = QTimer(self)
        self.link_timer.timeout.connect(self._poll_link_state)

    @property
    def network_model(self):
        return self._host.network_model

    @property
    def is_closing(self) -> bool:
        return self._host.closing or bool(getattr(self._host.app, "_closing", False))

    @property
    def bmc_ip(self) -> str:
        return self.network_config.bmc_ip

    def apply_bmc_state_from_result(self, result: object) -> None:
        if isinstance(result, dict) and "bmc_online" in result:
            self._set_bmc_online(bool(result["bmc_online"]))

    def startup(self) -> None:
        if os.environ.get("FRUTOOL_SMOKE") == "1" or os.environ.get("FRUTOOL_DEMO_TOPO") == "1" or os.environ.get("FRUTOOL_DEMO_SWAP") == "1":
            return
        _cleanup_legacy_nic_ip_backup()
        self._startup_retry_active = True
        self._startup_network_attempt = 0
        self._startup_network_timer.start(NETWORK_STARTUP_DELAY_MS)
        self.link_timer.start(LINK_POLL_INTERVAL_MS)
        self._bmc_probe_thread = BMCProbeThread(
            self._on_bmc_probe_state,
            self._on_local_probe_state,
            lambda: self.network_config.bmc_ip,
            lambda: self.network_config.local_ip,
            lambda: self._link_up,
        )
        self._bmc_probe_thread.start()

    def shutdown(self) -> None:
        self.link_timer.stop()
        self._startup_network_timer.stop()
        self._network_debounce_timer.stop()
        if self._bmc_probe_thread:
            self._bmc_probe_thread.stop()
            self._bmc_probe_thread.join(timeout=BMC_PROBE_JOIN_TIMEOUT_S)
            self._bmc_probe_thread = None
        if self._dhcp_server:
            self._host.log("info", "DHCP stopping on application shutdown")
            self._dhcp_server.stop()
            self._dhcp_server = None
        self._dhcp_sync_key = None

    @pyqtProperty(bool, notify=bmcOnlineChanged)
    def bmcOnline(self) -> bool:
        return self._bmc_online

    @pyqtProperty(bool, notify=localOnlineChanged)
    def localOnline(self) -> bool:
        return self._local_online

    @pyqtProperty(str, notify=networkSummaryChanged)
    def networkSummary(self) -> str:
        return self._network_summary

    @pyqtProperty(str, notify=networkSummaryChanged)
    def networkIpWarning(self) -> str:
        return self._network_ip_warning

    @pyqtProperty(bool, notify=networkRefreshingChanged)
    def networkRefreshing(self) -> bool:
        return self._network_refresh_running

    @pyqtProperty(int, notify=selectedNetworkIndexChanged)
    def selectedNetworkIndex(self) -> int:
        return self._selected_network_index

    @pyqtSlot(int)
    def setSelectedNetworkIndex(self, index: int) -> None:
        if index == self._selected_network_index:
            return
        self._selected_network_index = index
        self.selectedNetworkIndexChanged.emit()
        self._schedule_network_changed()

    @pyqtProperty(str, notify=bmcIpChanged)
    def bmcIp(self) -> str:
        return self.network_config.bmc_ip

    @pyqtProperty(str, notify=localIpChanged)
    def localIp(self) -> str:
        return self.network_config.local_ip

    @pyqtSlot()
    def _run_startup_network_refresh(self) -> None:
        if self.is_closing:
            return
        initial = self._startup_network_attempt == 0
        self._startup_network_attempt += 1
        self.refreshNetworks(initial=initial)

    def _schedule_startup_network_retry(self) -> None:
        if not self._startup_retry_active or self.is_closing:
            return
        if self._startup_network_attempt >= NETWORK_STARTUP_MAX_ATTEMPTS:
            self._startup_retry_active = False
            self._host.log(
                "warning",
                "启动时未能自动获取网卡，请点击连接页的「刷新网卡」手动重试。",
            )
            return
        remaining = NETWORK_STARTUP_MAX_ATTEMPTS - self._startup_network_attempt
        self._host.log(
            "info",
            f"暂未检测到可用网卡，约 {NETWORK_STARTUP_RETRY_MS // 1000} 秒后自动重试"
            f"（剩余 {remaining} 次）…",
        )
        self._startup_network_timer.start(NETWORK_STARTUP_RETRY_MS)

    @pyqtSlot(bool)
    def refreshNetworks(self, initial: bool = False) -> None:
        if self._network_refresh_running:
            return
        self._network_refresh_running = True
        self.networkRefreshingChanged.emit()

        def job(_log: LogCallback):
            return run_enumerate_networks_job(_log)

        self._host.run_worker(
            job,
            lambda choices: self._apply_network_choices(choices, initial),
            on_error=self._on_network_refresh_error,
        )

    def _finish_network_refresh(self) -> None:
        self._network_refresh_running = False
        self.networkRefreshingChanged.emit()

    def _on_network_refresh_error(self, message: str) -> None:
        self._finish_network_refresh()
        self._host.log("error", f"IPv4 refresh failed: {message}")
        if self._startup_retry_active:
            self._schedule_startup_network_retry()

    def _apply_network_choices(self, choices: object, initial: bool = False) -> None:
        self._finish_network_refresh()
        previous_ip = self.network_config.local_ip
        self.network_choices, index = normalize_network_choices(
            choices, previous_ip, _preferred_bmc_nic_index
        )
        self._host.network_model.setChoices(self.network_choices)
        self._selected_network_index = index
        self.selectedNetworkIndexChanged.emit()
        self._apply_network_changed()
        self._host.log("info", network_refresh_log_message(initial))
        if self._startup_retry_active:
            if network_choices_usable(self.network_choices):
                self._startup_retry_active = False
            else:
                self._schedule_startup_network_retry()

    def _current_network_choice(self) -> Optional[NetworkChoice]:
        return self._host.network_model.choiceAt(self._selected_network_index)

    def _schedule_network_changed(self) -> None:
        self._network_debounce_timer.stop()
        self._network_debounce_timer.start(NETWORK_CHANGE_DEBOUNCE_MS)

    def _apply_network_changed(self) -> None:
        choice = self._current_network_choice()
        self.network_config, self._network_summary = config_after_choice(choice)
        self._network_ip_warning = format_network_ip_warning(choice)
        self._host.log("info", f"网卡配置：{self._network_summary}")
        if self._network_ip_warning:
            self._host.log("warning", self._network_ip_warning)
        self.networkSummaryChanged.emit()
        self.bmcIpChanged.emit()
        self.localIpChanged.emit()
        self._local_online = False
        self.localOnlineChanged.emit()
        self._probe_local_ip_async()
        # Do not clear link_up — avoids "链路未知" pause on every refresh.
        self._set_bmc_online(False)
        if not self.network_config.local_ip:
            self._local_online = False
            self.localOnlineChanged.emit()
        # A BMC may bring its PHY up and send Discover at any point during boot.
        # Start listening as soon as a gated static configuration is known,
        # even while Windows still reports the cable state as down or unknown.
        self._sync_dhcp()
        QTimer.singleShot(0, self._poll_link_state)

    def _selected_interface_alias(self) -> Optional[str]:
        choice = self._current_network_choice()
        return choice.alias if choice and choice.alias else None

    def _poll_link_state(self) -> None:
        if self.is_closing or self._link_poll_in_flight:
            return
        alias = self._selected_interface_alias()
        if not alias:
            return
        poll_alias = alias
        self._link_poll_in_flight = True

        def job(_log: LogCallback):
            return run_link_poll_job(poll_alias, _log)

        def done(result: object):
            self._link_poll_in_flight = False
            if self.is_closing or not isinstance(result, dict):
                return
            if result.get("link_up") is None:
                return
            if result.get("alias") != self._selected_interface_alias():
                return
            self._apply_link_state(str(result["alias"]), bool(result["link_up"]))

        self._host.run_worker(
            job,
            done,
            on_error=lambda _m: setattr(self, "_link_poll_in_flight", False),
        )

    def _apply_link_state(self, alias: str, link_up: bool) -> None:
        prev = self._link_up
        self._link_up = link_up
        log_entry, bmc_offline = describe_link_transition(prev, link_up, alias)
        if log_entry:
            level, message = log_entry
            self._host.log(level, message)
        if bmc_offline:
            self._set_bmc_online(False)
        if not link_up:
            # Keep DHCP running across unplug (auto-swap). No packets arrive while down.
            return
        if prev is False:
            # Was down, now up — re-enumerate so office DHCP client vs static is detected.
            self.refreshNetworks(initial=False)
            return
        # First poll after config (prev is None) or still up: sync gate only.
        self._sync_dhcp()

    def _get_network_config(self) -> NetworkConfig:
        return self.network_config

    def _sync_dhcp(self) -> None:
        choice = self._current_network_choice()
        run, pause_reason = should_run_dhcp(choice, self._link_up)
        sync_key = (
            run,
            self.network_config.local_ip,
            self.network_config.bmc_ip,
            self.network_config.prefix_length,
            choice.alias if choice else "",
            pause_reason,
        )
        server_healthy = bool(self._dhcp_server and self._dhcp_server.is_alive())
        if self._dhcp_sync_key == sync_key and (
            server_healthy if run else self._dhcp_server is None
        ):
            return
        self._dhcp_server = restart_dhcp_server(
            self._dhcp_server,
            self._host.log,
            self._get_network_config,
            on_ack_sent=self._on_dhcp_ack_sent,
            should_run=run,
            pause_reason=pause_reason,
        )
        self._dhcp_sync_key = sync_key

    def _on_dhcp_ack_sent(self, mac: str, ip: str) -> None:
        self._grace_until = time.monotonic() + 3.0
        self._host.log("info", f"DHCP probe grace 3s after ACK to {mac} ({ip})")

    def _on_bmc_probe_state(self, online: bool) -> None:
        if not online and time.monotonic() < self._grace_until:
            return
        self._set_bmc_online(online)

    def _on_local_probe_state(self, online: bool) -> None:
        self._local_online = online
        self.localOnlineChanged.emit()

    def _set_bmc_online(self, online: bool) -> None:
        if online == self._bmc_online:
            return
        self._bmc_online = online
        self.bmcOnlineChanged.emit(online)

    def _probe_local_ip_async(self) -> None:
        if self._local_probe_in_flight:
            return
        local_ip = self.network_config.local_ip
        if not local_ip:
            if self._local_online:
                self._local_online = False
                self.localOnlineChanged.emit()
            return
        self._local_probe_in_flight = True
        probe_ip = local_ip

        def job(_log: LogCallback):
            return run_local_ip_probe_job(probe_ip, BMC_PING_TIMEOUT_MS, _log)

        def done(result: object):
            self._local_probe_in_flight = False
            if self.is_closing or not isinstance(result, dict):
                return
            if result.get("ip") != self.network_config.local_ip:
                return
            self._local_online = bool(result.get("online"))
            self.localOnlineChanged.emit()

        self._host.run_worker(
            job,
            done,
            on_error=lambda _m: setattr(self, "_local_probe_in_flight", False),
        )
