"""Network summary and selection helpers (no Qt)."""
from __future__ import annotations

from typing import Callable, Optional

from frutool.infrastructure.network import (
    IPV4_ORIGIN_DHCP,
    NetworkChoice,
    NetworkConfig,
    explain_unusable_host_ipv4,
)


def pick_network_index(
    choices: list[NetworkChoice],
    previous_ip: str,
    preferred_index: Callable[[list[NetworkChoice]], int],
) -> int:
    if not choices:
        return 0
    for i, choice in enumerate(choices):
        if choice.ipv4 == previous_ip:
            return i
    return preferred_index(choices)


def format_network_ip_warning(choice: Optional[NetworkChoice]) -> str:
    if not isinstance(choice, NetworkChoice):
        return (
            "未检测到可用网卡。请连接有线网线并为网卡配置静态 IPv4"
            "（例如 192.168.1.2/24）后点击「刷新网卡」。"
        )
    if not choice.ipv4:
        return (
            f"网卡「{choice.alias}」未连接或无 IPv4。"
            "请连接网线并配置静态 IPv4（例如 192.168.1.2，子网掩码 255.255.255.0）"
            "后点击「刷新网卡」。"
        )
    issue = explain_unusable_host_ipv4(choice.ipv4, choice.prefix_length or 24)
    if issue:
        return (
            f"当前网卡 IP {choice.ipv4} 无法为 BMC 提供 DHCP（{issue}）。"
            "请在 Windows「控制面板 → 网络和 Internet → 网络连接」中为该网卡配置静态 IPv4"
            "（例如 192.168.1.2，子网掩码 255.255.255.0）后点击「刷新网卡」。"
        )
    if choice.ipv4_origin == IPV4_ORIGIN_DHCP:
        return (
            "当前网卡为 Windows DHCP 客户端（办公上网），内置 DHCP 已暂停，避免干扰局域网。"
            "产测请为该网卡配置静态 IPv4 后点击「刷新网卡」。"
        )
    return ""


def format_network_summary(config: NetworkConfig, choice: Optional[NetworkChoice]) -> str:
    ip_warning = format_network_ip_warning(choice)
    if not config.local_ip:
        base = "来源：无可用地址；本机 IPv4：—；分配给 BMC：—；掩码：—"
        if ip_warning:
            return base + "；" + ip_warning
        return base + "；请连接网线并配置静态 IP 后刷新"
    if isinstance(choice, NetworkChoice) and choice.ipv4 and not ip_warning:
        source = "网卡"
        extra = ""
    elif isinstance(choice, NetworkChoice):
        source = "网卡"
        extra = ip_warning or "；请在 Windows 网络设置中为该网卡配置静态 IP（如 192.168.1.2/24）后点刷新"
    else:
        source = "无"
        extra = "；未检测到有线网卡，请刷新后选择以太网/USB 网卡"
    base = (
        f"来源：{source}；本机 IPv4：{config.local_ip}/{config.prefix_length}；"
        f"分配给 BMC：{config.bmc_ip}；掩码：{config.subnet_mask}"
    )
    if not extra:
        return base
    if extra.startswith("；"):
        return base + extra
    return base + "；" + extra
