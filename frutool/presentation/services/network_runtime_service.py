"""Network worker jobs and DHCP lifecycle helpers (no Qt)."""
from __future__ import annotations

import concurrent.futures
import threading
from typing import Callable, Optional

from frutool.config import NETWORK_ENUM_JOB_TIMEOUT_S, LogCallback
from frutool.domain.dhcp import DHCPServer
from frutool.domain.ipmi import probe_bmc_ping
from frutool.infrastructure.network import (
    IPV4_ORIGIN_DHCP,
    NetworkChoice,
    NetworkConfig,
    enumerate_ipv4_interfaces,
    is_dhcp_usable_host_ipv4,
    make_network_config,
    query_adapter_link_up,
)
from frutool.presentation.services.network_service import format_network_summary, pick_network_index

_dhcp_restart_lock = threading.Lock()


def run_enumerate_networks_job(log: LogCallback) -> list[NetworkChoice]:
    """Enumerate adapters with a hard job-level timeout (independent of per-command limits)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(enumerate_ipv4_interfaces)
        try:
            return future.result(timeout=NETWORK_ENUM_JOB_TIMEOUT_S)
        except concurrent.futures.TimeoutError as exc:
            log(
                "warning",
                f"网卡枚举超时（>{NETWORK_ENUM_JOB_TIMEOUT_S}s），请稍后点击「刷新网卡」重试。",
            )
            raise TimeoutError(
                f"network enumeration exceeded {NETWORK_ENUM_JOB_TIMEOUT_S}s"
            ) from exc


def run_link_poll_job(alias: str, _log: LogCallback) -> dict:
    return {"alias": alias, "link_up": query_adapter_link_up(alias)}


def run_local_ip_probe_job(ip: str, timeout_ms: int, _log: LogCallback) -> dict:
    return {"ip": ip, "online": probe_bmc_ping(ip, timeout_ms)}


def normalize_network_choices(
    choices: object,
    previous_ip: str,
    preferred_index: Callable[[list[NetworkChoice]], int],
) -> tuple[list[NetworkChoice], int]:
    if not isinstance(choices, list):
        choices = []
    if not choices:
        return [], 0
    index = pick_network_index(choices, previous_ip, preferred_index)
    return list(choices), index


def config_after_choice(choice: Optional[NetworkChoice]) -> tuple[NetworkConfig, str]:
    config = make_network_config(choice)
    summary = format_network_summary(config, choice)
    return config, summary


def should_run_dhcp(
    choice: Optional[NetworkChoice],
    link_up: Optional[bool],
) -> tuple[bool, str]:
    """Return (run, pause_reason).

    Pause only for an explicit Windows DHCP client (office LAN) or missing/unusable IPv4.
    Do **not** pause on link down — auto-swap unplugs the cable between boards; keeping
    DHCP listening avoids missing the new BMC Discover after replug.
    """
    del link_up  # retained for call-site compatibility; link state does not gate DHCP
    if not isinstance(choice, NetworkChoice) or not choice.ipv4:
        return False, "未选定可用网卡 IPv4"
    if not is_dhcp_usable_host_ipv4(choice.ipv4, choice.prefix_length or 24):
        return False, f"本机 IP {choice.ipv4} 不可用于 BMC DHCP"
    if choice.ipv4_origin == IPV4_ORIGIN_DHCP:
        return (
            False,
            "当前网卡为 Windows DHCP 客户端（办公上网），内置 DHCP 已暂停，避免干扰局域网",
        )
    return True, ""


def describe_link_transition(
    prev: Optional[bool], link_up: bool, alias: str
) -> tuple[Optional[tuple[str, str]], bool]:
    """Return (level, message) log tuple if any, and whether BMC should go offline."""
    if prev is None:
        if link_up:
            return (
                (
                    "info",
                    f"网卡链路已连接：{alias}，同步 DHCP"
                    "（若 BMC 长时间未获 IP，请插拔网线）…",
                ),
                False,
            )
        return (None, True)
    if prev == link_up:
        return (None, False)
    if link_up:
        return (
            (
                "info",
                f"网卡链路已连接：{alias}，刷新网卡并同步 DHCP…",
            ),
            False,
        )
    return (("info", f"网卡链路已断开：{alias}（DHCP 保持运行，便于换板后新板获取地址）"), True)


def restart_dhcp_server(
    old_server: Optional[DHCPServer],
    log: LogCallback,
    get_config: Callable[[], NetworkConfig],
    on_ack_sent: Optional[Callable[[str, str], None]] = None,
    *,
    should_run: bool = True,
    pause_reason: str = "",
) -> Optional[DHCPServer]:
    with _dhcp_restart_lock:
        config = get_config()
        if old_server:
            log(
                "info",
                f"DHCP stopping (local={config.local_ip}, bmc={config.bmc_ip})",
            )
            old_server.stop()
            old_server.join(timeout=2.5)
            log("info", "DHCP server stopped")
        if not should_run:
            reason = pause_reason or "gate closed"
            log("info", f"DHCP paused: {reason}")
            return None
        log(
            "info",
            f"DHCP starting (local={config.local_ip}, bmc={config.bmc_ip})",
        )
        server = DHCPServer(log, get_config, on_ack_sent=on_ack_sent)
        server.start()
        return server


def network_refresh_log_message(initial: bool) -> str:
    return "启动时已自动刷新网卡" if initial else "IPv4 列表已刷新"


def network_choices_usable(choices: object) -> bool:
    """True when at least one enumerated adapter reports an IPv4 address."""
    if not isinstance(choices, list) or not choices:
        return False
    return any(getattr(choice, "ipv4", "") for choice in choices)
