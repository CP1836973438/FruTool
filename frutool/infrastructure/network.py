"""Network adapter enumeration and BMC addressing."""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from frutool.config import (
    NIC_IP_BACKUP_JSON,
    NETWORK_ENUM_IPCONFIG_TIMEOUT_S,
    NETWORK_ENUM_POWERSHELL_PROBE_TIMEOUT_S,
    NETWORK_ENUM_POWERSHELL_TIMEOUT_S,
)

_IPCONFIG_ADAPTER_HEADER = re.compile(
    r"^(?:以太网适配器 |Ethernet adapter )",
    re.I,
)
_LOCAL_CONNECTION_ALIAS = re.compile(r"^(?:本地连接|Local Area Connection)\s*\*", re.I)

# Windows Get-NetIPAddress PrefixOrigin / ipconfig DHCP Enabled
IPV4_ORIGIN_MANUAL = "Manual"
IPV4_ORIGIN_DHCP = "Dhcp"
IPV4_ORIGIN_UNKNOWN = "Unknown"


@dataclass(frozen=True)
class NetworkChoice:
    alias: str
    description: str
    ipv4: str
    prefix_length: int = 24
    status: str = ""
    mac: str = ""
    ipv4_origin: str = IPV4_ORIGIN_UNKNOWN

    @property
    def label(self) -> str:
        text = f"{self.alias} {self.description}".lower()
        usb_tag = "[USB] " if "usb" in text and not _is_wifi_text(text) else ""
        desc = f" — {self.description}" if self.description and self.description != self.alias else ""
        status = f" [{self.status}]" if self.status else ""
        origin_tag = ""
        if self.ipv4 and self.ipv4_origin == IPV4_ORIGIN_DHCP:
            origin_tag = " [DHCP]"
        elif self.ipv4 and self.ipv4_origin == IPV4_ORIGIN_MANUAL:
            origin_tag = " [静态]"
        if self.ipv4:
            issue = explain_unusable_host_ipv4(self.ipv4, self.prefix_length)
            unusable_tag = " [不可用]" if issue else ""
            return (
                f"{usb_tag}{self.alias}  {self.ipv4}/{self.prefix_length}"
                f"{unusable_tag}{origin_tag}{status}{desc}"
            )
        return f"{usb_tag}{self.alias}  未连接/无 IPv4{status}{desc}"


def normalize_ipv4_origin(value: object) -> str:
    """Map Windows PrefixOrigin / Dhcp / free-text to Manual, Dhcp, or Unknown.

    PowerShell ``ConvertTo-Json`` often emits PrefixOrigin as an int enum:
    Other=0, Manual=1, WellKnown=2, Dhcp=3, RouterAdvertisement=4.
    """
    if isinstance(value, bool):
        return IPV4_ORIGIN_DHCP if value else IPV4_ORIGIN_MANUAL
    if isinstance(value, (int, float)):
        code = int(value)
        if code == 1:
            return IPV4_ORIGIN_MANUAL
        if code == 3:
            return IPV4_ORIGIN_DHCP
        return IPV4_ORIGIN_UNKNOWN
    text = str(value or "").strip().lower()
    if not text:
        return IPV4_ORIGIN_UNKNOWN
    if text.isdigit():
        return normalize_ipv4_origin(int(text))
    if text in ("manual", "静态", "static", "disabled", "false", "no", "否"):
        return IPV4_ORIGIN_MANUAL
    if text in ("dhcp", "dhc", "yes", "是", "enabled", "已启用", "true"):
        return IPV4_ORIGIN_DHCP
    return IPV4_ORIGIN_UNKNOWN


def resolve_ipv4_origin(*values: object) -> str:
    """Prefer explicit Dhcp, then Manual, else Unknown across multiple Windows signals."""
    normalized = [normalize_ipv4_origin(v) for v in values if v is not None and str(v).strip() != ""]
    if IPV4_ORIGIN_DHCP in normalized:
        return IPV4_ORIGIN_DHCP
    if IPV4_ORIGIN_MANUAL in normalized:
        return IPV4_ORIGIN_MANUAL
    return IPV4_ORIGIN_UNKNOWN


@dataclass(frozen=True)
class NetworkConfig:
    local_ip: str
    bmc_ip: str
    subnet_mask: str
    prefix_length: int
    interface_label: str


def _startup_flags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _find_powershell() -> str:
    candidates = [
        "powershell",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
        "pwsh",
        r"C:\Program Files\PowerShell\7\pwsh.exe",
    ]
    for c in candidates:
        try:
            subprocess.run(
                [c, "-Command", "exit"],
                capture_output=True,
                timeout=NETWORK_ENUM_POWERSHELL_PROBE_TIMEOUT_S,
                creationflags=_startup_flags(),
            )
            return c
        except (FileNotFoundError, OSError):
            continue
    return "powershell"


_POWERSHELL_EXE = _find_powershell()


def _valid_ipv4(value: str) -> bool:
    return is_dhcp_usable_host_ipv4(value)


def _parse_ipv4(value: str) -> Optional[ipaddress.IPv4Address]:
    try:
        addr = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if addr.version != 4:
        return None
    return addr


def explain_unusable_host_ipv4(ip: str, prefix_length: int = 24) -> Optional[str]:
    """Return why an IPv4 cannot be used as the local host for BMC DHCP, or None if usable."""
    addr = _parse_ipv4(ip)
    if addr is None:
        return "IPv4 地址格式无效"

    if addr == ipaddress.ip_address("255.255.255.255"):
        return "255.255.255.255 受限广播地址，不能分配给设备"

    if addr in ipaddress.ip_network("0.0.0.0/8"):
        return "0.0.0.0/8 未指定地址，无实际网络意义"

    if addr.is_loopback:
        return "127.0.0.0/8 环回地址，仅本机内部通信"

    if addr.is_link_local:
        return "169.254.x.x APIPA/链路本地地址，无法用于 DHCP"

    if addr.is_multicast:
        return "224.0.0.0–239.255.255.255 组播地址，不能用于单播"

    if addr.is_reserved:
        return "240.0.0.0/4 保留地址，无法使用"

    try:
        iface = ipaddress.ip_interface(f"{addr}/{prefix_length}")
        network = iface.network
        if addr == network.network_address:
            return f"{ip} 是网段网络地址 (x.x.x.0)，不能分配给设备"
        if addr == network.broadcast_address:
            return f"{ip} 是子网广播地址 (x.x.x.255)，不能分配给设备"
    except ValueError:
        pass

    return None


def is_dhcp_usable_host_ipv4(ip: str, prefix_length: int = 24) -> bool:
    return explain_unusable_host_ipv4(ip, prefix_length) is None


def _is_wifi_text(text: str) -> bool:
    text = text.lower()
    return any(word in text for word in ("wi-fi", "wifi", "wireless", "wlan", "无线"))


def _is_virtual_text(text: str) -> bool:
    text = text.lower()
    if any(word in text for word in ("virtual", "vmware", "hyper-v", "loopback", "bluetooth", "蓝牙", "环回", "wintun", "tun", "meta", "clash", "sing-box", "singbox", "tap-windows")):
        return True
    return "198.18." in text


def _should_exclude_adapter(choice: NetworkChoice) -> bool:
    text = f"{choice.alias} {choice.description} {choice.ipv4}"
    if _is_virtual_text(text):
        return True
    if _LOCAL_CONNECTION_ALIAS.match(choice.alias.strip()):
        return True
    desc_lower = choice.description.lower()
    if "wi-fi direct" in desc_lower or "microsoft wi-fi direct" in desc_lower:
        return True
    return False


def prefix_to_mask(prefix_length: int) -> str:
    try:
        return str(ipaddress.ip_network(f"0.0.0.0/{prefix_length}").netmask)
    except ValueError:
        return "255.255.255.0"


def derive_bmc_ip(local_ip: str, prefix_length: int) -> str:
    try:
        network = ipaddress.ip_network(f"{local_ip}/{prefix_length}", strict=False)
        host_ip = ipaddress.ip_address(local_ip)
        base = int(network.network_address)
        for host in (100, 101, 200, 10, 50):
            candidate = ipaddress.ip_address(base + host)
            if candidate in network and candidate != host_ip and candidate not in (
                network.network_address,
                network.broadcast_address,
            ):
                return str(candidate)
        for candidate in network.hosts():
            if candidate != host_ip:
                return str(candidate)
    except ValueError:
        pass
    parts = local_ip.split(".")
    if len(parts) == 4:
        parts[-1] = "100" if parts[-1] != "100" else "101"
        return ".".join(parts)
    return "192.168.1.100"


def make_network_config(choice: Optional[NetworkChoice]) -> NetworkConfig:
    prefix = (choice.prefix_length or 24) if choice else 24
    if (
        choice is None
        or not choice.ipv4
        or not is_dhcp_usable_host_ipv4(choice.ipv4, prefix)
    ):
        # Do not invent a fake host IP when the NIC has no usable IPv4 —
        # that made "本机" look online while the adapter was Disconnected.
        return NetworkConfig("", "", "255.255.255.0", 24, "Unavailable")
    return NetworkConfig(
        choice.ipv4,
        derive_bmc_ip(choice.ipv4, prefix),
        prefix_to_mask(prefix),
        prefix,
        choice.label,
    )


def _mask_to_prefix_length(mask: str) -> int:
    try:
        return ipaddress.ip_network(f"0.0.0.0/{mask}", strict=False).prefixlen
    except ValueError:
        return 24


def _subnet_broadcast_addr(local_ip: str, prefix_length: int) -> str:
    try:
        iface = ipaddress.ip_interface(f"{local_ip}/{prefix_length}")
        return str(iface.network.broadcast_address)
    except ValueError:
        return "255.255.255.255"


def _bmc_nic_score(item: NetworkChoice) -> tuple[int, str]:
    text = f"{item.alias} {item.description}".lower()
    value = 20
    if not item.ipv4:
        value += 40
    elif explain_unusable_host_ipv4(item.ipv4, item.prefix_length):
        value += 55
    if item.status.lower() in ("up", "connected"):
        value -= 12
    if any(word in text for word in ("usb", "ax88", "asix")) and not _is_wifi_text(text):
        value -= 18
    elif any(word in text for word in ("ethernet", "realtek", "intel", "gbe", "lan", "以太网")):
        value -= 10
    if _is_wifi_text(text):
        value += 30
    if _is_virtual_text(text):
        value += 50
    return value, item.alias


def _finalize_network_choices(choices: list[NetworkChoice]) -> list[NetworkChoice]:
    unique = {(item.alias, item.ipv4, item.status): item for item in choices}
    choices = list(unique.values())
    return sorted(choices, key=_bmc_nic_score)


def _preferred_bmc_nic_index(choices: list[NetworkChoice]) -> int:
    if not choices:
        return 0
    best = min(range(len(choices)), key=lambda i: _bmc_nic_score(choices[i]))
    return best


def _normalize_json_array(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _choices_from_powershell_row(row: dict) -> list[NetworkChoice]:
    alias = str(row.get("InterfaceAlias") or "Network Adapter")
    desc = str(row.get("InterfaceDescription") or alias)
    status = str(row.get("Status") or "")
    mac = str(row.get("MacAddress") or "")
    ips = _normalize_json_array(row.get("IPv4"))
    prefixes = _normalize_json_array(row.get("PrefixLength"))
    origins = _normalize_json_array(row.get("PrefixOrigin"))
    dhcp_flags = _normalize_json_array(row.get("Dhcp"))
    dhcp_flag = dhcp_flags[0] if dhcp_flags else ""
    choices: list[NetworkChoice] = []
    if not ips:
        candidate = NetworkChoice(alias, desc, "", 24, status or "No IPv4", mac=mac)
        if not _should_exclude_adapter(candidate):
            choices.append(candidate)
        return choices
    added = False
    for i, ip in enumerate(ips):
        ip_str = str(ip).strip()
        if _parse_ipv4(ip_str) is None:
            continue
        prefix_raw = prefixes[i] if i < len(prefixes) else 24
        try:
            prefix = int(prefix_raw)
        except (TypeError, ValueError):
            prefix = 24
        origin_raw = origins[i] if i < len(origins) else ""
        # Prefer interface Dhcp Enabled/Disabled, then PrefixOrigin (may be int in JSON).
        origin = resolve_ipv4_origin(dhcp_flag, origin_raw)
        candidate = NetworkChoice(
            alias, desc, ip_str, prefix, status, mac=mac, ipv4_origin=origin
        )
        if not _should_exclude_adapter(candidate):
            choices.append(candidate)
            added = True
    if ips and not added:
        candidate = NetworkChoice(alias, desc, "", 24, status or "No IPv4", mac=mac)
        if not _should_exclude_adapter(candidate):
            choices.append(candidate)
    return choices


def _enumerate_via_ipconfig() -> list[NetworkChoice]:
    choices: list[NetworkChoice] = []
    try:
        result = subprocess.run(
            ["ipconfig", "/all"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=NETWORK_ENUM_IPCONFIG_TIMEOUT_S,
            creationflags=_startup_flags(),
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        blocks = re.split(r"\r?\n\r?\n", result.stdout)
        adapter_prefixes = (
            "以太网适配器 ",
            "无线局域网适配器 ",
            "Ethernet adapter ",
            "Wireless LAN adapter ",
        )
        for block in blocks:
            lines = [line.rstrip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            header = lines[0].strip()
            if not header.endswith(":"):
                continue
            if re.search(r"loopback|环回", header, re.I):
                continue
            if not _IPCONFIG_ADAPTER_HEADER.match(header):
                continue
            full_name = header[:-1].strip()
            alias = full_name
            desc = full_name
            for prefix in adapter_prefixes:
                if full_name.startswith(prefix):
                    alias = full_name[len(prefix) :].strip()
                    break
            ipv4 = None
            prefix_len = 24
            dhcp_enabled: Optional[bool] = None
            for line in lines[1:]:
                if re.search(r"DHCP\s*(已)?启用|DHCP Enabled", line, re.I):
                    if re.search(r":\s*(是|Yes)\s*$", line, re.I):
                        dhcp_enabled = True
                    elif re.search(r":\s*(否|No)\s*$", line, re.I):
                        dhcp_enabled = False
                if re.search(r"IPv4.*地址|IPv4 Address", line, re.I):
                    match = re.search(r":\s*([\d\.]+)", line)
                    if match:
                        ipv4 = match.group(1).split("(")[0].strip()
                if re.search(r"子网掩码|Subnet Mask", line, re.I):
                    match = re.search(r":\s*([\d\.]+)", line)
                    if match and _valid_ipv4(match.group(1)):
                        prefix_len = _mask_to_prefix_length(match.group(1))
            if dhcp_enabled is True:
                origin = IPV4_ORIGIN_DHCP
            elif dhcp_enabled is False:
                origin = IPV4_ORIGIN_MANUAL
            else:
                origin = IPV4_ORIGIN_UNKNOWN
            candidate = (
                NetworkChoice(alias, desc, ipv4, prefix_len, "Up", ipv4_origin=origin)
                if ipv4 and _parse_ipv4(ipv4) is not None
                else NetworkChoice(alias, desc, "", 24, "", ipv4_origin=origin)
            )
            if _should_exclude_adapter(candidate):
                continue
            choices.append(candidate)
    except Exception:
        return []
    return choices


def _enumerate_via_powershell() -> list[NetworkChoice]:
    choices: list[NetworkChoice] = []
    if sys.platform != "win32":
        return choices
    ps = (
        "$adapters = Get-NetAdapter -Physical -ErrorAction SilentlyContinue; "
        "if (-not $adapters) { $adapters = Get-NetAdapter -ErrorAction SilentlyContinue }; "
        "$ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.PrefixOrigin -ne 'WellKnown' }; "
        "$ifaces = Get-NetIPInterface -AddressFamily IPv4 -ErrorAction SilentlyContinue; "
        "$adapters | ForEach-Object { "
        "$a = $_; "
        "$addr = @($ips | Where-Object { $_.InterfaceIndex -eq $a.ifIndex }); "
        "$iface = @($ifaces | Where-Object { $_.InterfaceIndex -eq $a.ifIndex }) | Select-Object -First 1; "
        "$dhcp = if ($null -ne $iface) { [string]$iface.Dhcp } else { '' }; "
        "[pscustomobject]@{"
        "ifIndex=$a.ifIndex;"
        "InterfaceAlias=$a.Name;"
        "InterfaceDescription=$a.InterfaceDescription;"
        "MacAddress=$a.MacAddress;"
        "Status=$a.Status;"
        "IPv4=@($addr.IPAddress);"
        "PrefixLength=@($addr.PrefixLength);"
        "PrefixOrigin=@($addr | ForEach-Object { [string]$_.PrefixOrigin });"
        "Dhcp=$dhcp"
        "} "
        "} | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            [_POWERSHELL_EXE, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=NETWORK_ENUM_POWERSHELL_TIMEOUT_S,
            creationflags=_startup_flags(),
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            rows = data if isinstance(data, list) else [data]
            for row in rows:
                choices.extend(_choices_from_powershell_row(row))
    except Exception:
        return []
    return choices


def query_adapter_bytes_total(interface_alias: str) -> Optional[int]:
    """Return cumulative RX+TX bytes for the adapter, or None if unavailable."""
    if sys.platform != "win32" or not interface_alias:
        return None
    alias_json = json.dumps(interface_alias)
    ps = (
        f"$s = Get-NetAdapterStatistics -Name {alias_json} -ErrorAction SilentlyContinue; "
        "if ($null -eq $s) { exit 1 }; "
        "[Console]::Write([int64]($s.ReceivedBytes + $s.SentBytes))"
    )
    try:
        result = subprocess.run(
            [_POWERSHELL_EXE, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=4,
            creationflags=_startup_flags(),
        )
        if result.returncode != 0:
            return None
        text = (result.stdout or "").strip()
        if not text:
            return None
        return int(text)
    except Exception:
        return None


def query_adapter_link_up(interface_alias: str) -> Optional[bool]:
    """Return True if adapter link is up, False if down/disconnected, None if unknown."""
    if sys.platform != "win32" or not interface_alias:
        return None
    alias_json = json.dumps(interface_alias)
    ps = f"(Get-NetAdapter -Name {alias_json} -ErrorAction SilentlyContinue).Status"
    try:
        result = subprocess.run(
            [_POWERSHELL_EXE, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=4,
            creationflags=_startup_flags(),
        )
        if result.returncode != 0:
            return None
        status = (result.stdout or "").strip()
        if not status:
            return None
        if status.lower() == "up":
            return True
        if status.lower() in ("disconnected", "not present", "disabled"):
            return False
        return None
    except Exception:
        return None


def _cleanup_legacy_nic_ip_backup() -> None:
    try:
        if os.path.isfile(NIC_IP_BACKUP_JSON):
            os.remove(NIC_IP_BACKUP_JSON)
    except OSError:
        pass


def enumerate_ipv4_interfaces() -> list[NetworkChoice]:
    choices: list[NetworkChoice] = []
    if sys.platform == "win32":
        ps_choices = _enumerate_via_powershell()
        if not ps_choices:
            choices = [c for c in _enumerate_via_ipconfig() if not _should_exclude_adapter(c)]
        else:
            merged: dict[str, NetworkChoice] = {}
            for choice in ps_choices:
                if _should_exclude_adapter(choice):
                    continue
                existing = merged.get(choice.alias)
                if existing is None:
                    merged[choice.alias] = choice
                elif is_dhcp_usable_host_ipv4(existing.ipv4, existing.prefix_length):
                    continue
                elif _parse_ipv4(choice.ipv4) is not None:
                    merged[choice.alias] = choice
            for choice in _enumerate_via_ipconfig():
                if _should_exclude_adapter(choice):
                    continue
                existing = merged.get(choice.alias)
                if existing is None:
                    merged[choice.alias] = choice
                elif is_dhcp_usable_host_ipv4(existing.ipv4, existing.prefix_length):
                    continue
                elif _parse_ipv4(choice.ipv4) is not None:
                    merged[choice.alias] = choice
            choices = list(merged.values())
    if not choices:
        try:
            for _, _, _, _, sockaddr in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                ip = sockaddr[0]
                if _valid_ipv4(ip):
                    choices.append(NetworkChoice("Default Network", "socket hostname", ip, 24, "Up"))
        except Exception:
            pass
    return _finalize_network_choices(choices)
