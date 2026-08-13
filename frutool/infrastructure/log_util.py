"""Log classification and formatting helpers."""
from __future__ import annotations

import re

# Network / DHCP tab — any message mentioning DHCP or local NIC / UDP 67 lifecycle.
_DHCP_LOG_PATTERNS = (
    re.compile(r"\bDHCP\b", re.I),
    re.compile(r"Cannot bind UDP\s*67", re.I),
    re.compile(r"UDP\s*:?\s*67", re.I),
    re.compile(r"netstat did not list.*UDP.*:?\s*67", re.I),
    re.compile(r"Assigned .+ to .+; local IP", re.I),
    re.compile(r"网卡链路", re.I),
    re.compile(r"网卡配置", re.I),
    re.compile(r"IPv4", re.I),
    re.compile(r"probe grace", re.I),
    re.compile(r"no pending lease", re.I),
    re.compile(r"DHCP bind failure", re.I),
    re.compile(r"conflicting service", re.I),
    re.compile(r"Internet 连接共享", re.I),
    re.compile(r"刷新网卡", re.I),
)

_UDP67_OCCUPANT_RE = re.compile(
    r"^\s*UDP\s+(\S+):67\s+\S+(?:\s+\S+)*\s+(\d+)\s*$",
    re.I,
)

_DHCP_BIND_HINTS = (
    "VMware 虚拟网卡 / VMnet DHCP（vmnat.exe、vmnetdhcp.exe）",
    "Hyper-V 虚拟交换机 DHCP",
    "Windows ICS（Internet 连接共享）",
    "其它占用 UDP 67 的 DHCP 服务或产测工具",
)

_FRU_LOG_PATTERNS = (
    re.compile(r"\bFRU\b", re.I),
    re.compile(r"\bfru\s+(list|edit|read|print)\b", re.I),
    re.compile(r"field\s+\S+\s+\d+\s+(written|failed)", re.I),
    re.compile(r"批量刷写", re.I),
    re.compile(r"Board Serial", re.I),
    re.compile(r"ipmitool.*\bfru\b", re.I),
    re.compile(r"\[Auto\]", re.I),
    re.compile(r"Step [12] started", re.I),
    re.compile(r"Exporting FRU|FRU export|FRU backup|FRU clone", re.I),
    re.compile(r"换板|回滚|Rollback", re.I),
    re.compile(r"SN 已确认", re.I),
    re.compile(r"Waiting for BMC .+ fru list", re.I),
    re.compile(r"FRU not ready|FRU wait timed out|BMC FRU ready", re.I),
)

_TOPO_LOG_PATTERNS = (
    re.compile(r"PcieEEpromTool", re.I),
    re.compile(r"Topology file", re.I),
    re.compile(r"Topology write", re.I),
    re.compile(r"Start data writing", re.I),
    re.compile(r"Writing data", re.I),
    re.compile(r"Successfully write data", re.I),
    re.compile(r"Verify Data", re.I),
    re.compile(r"写入 EEPROM|拓扑", re.I),
)


def _is_dhcp_log(message: str) -> bool:
    return any(p.search(message) for p in _DHCP_LOG_PATTERNS)


def _is_fru_log(message: str) -> bool:
    return any(p.search(message) for p in _FRU_LOG_PATTERNS)


def _is_topo_log(message: str) -> bool:
    return any(p.search(message) for p in _TOPO_LOG_PATTERNS)


def classify_log(message: str) -> set[str]:
    """Assign each log line to ``all`` plus at most one specialized tab."""
    categories = {"all"}
    if _is_dhcp_log(message):
        categories.add("dhcp")
    elif _is_fru_log(message):
        categories.add("fru")
    elif _is_topo_log(message):
        categories.add("topo")
    return categories


def format_log_html(theme_key: str, level: str, message: str, ts: str, *, log_color_fn) -> str:
    color = log_color_fn(theme_key, level)
    prefix = {"success": "SUCCESS", "error": "ERR", "warning": "WARN", "cmd": "$", "info": "INFO"}.get(level, "INFO")
    escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    return f'<span style="color:{color}">[{ts}] {prefix} {escaped}</span>'
