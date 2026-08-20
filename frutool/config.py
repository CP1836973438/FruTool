"""Application constants and paths."""
from __future__ import annotations

import glob
import json
import os
import shutil
import sys
from typing import Callable, Optional

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IPMITOOL_DIR_NAME = "ipmitool"
IPMITOOL_EXE_NAME = "ipmitool.exe"
PCIE_EEPROM_TOOL_NAME = "PcieEEpromTool.py"
DEFAULT_IPMITOOL_PATH = os.path.join(BASE_DIR, IPMITOOL_DIR_NAME, IPMITOOL_EXE_NAME)
DEFAULT_IPMITOOL_DIR = os.path.join(BASE_DIR, IPMITOOL_DIR_NAME)

BACKUP_DIR = os.path.join(BASE_DIR, "fru_backup")
LOG_DIR = os.path.join(BASE_DIR, "logs")
PCLE_DIR_NAME = "PCLE"
TOPO_CACHE_DIR = os.path.join(BACKUP_DIR, "topo_cache")
TOPO_INDEX_JSON = os.path.join(LOG_DIR, "topo_index.json")
TOPO_SCRIPT_PREF_JSON = os.path.join(LOG_DIR, "topo_prefs.json")
APP_ICON_NAME = "FRUTool.ico"
PCIE_EEPROM_TOOL_GLOB = "PcieEEpromTool*.py"

# PCLE archive naming: manufacturer in filename; platform codes (机型) are optional hints.
PCLE_MANUFACTURERS: tuple[str, ...] = (
    "FOXCONN",
    "H3C",
    "Maginfra",
    "Inspur",
    "Lenovo",
    "Changkuai",
    "Nettrix",
    "Inventec",
    "HuaQin",
    "Kunlun",
)
PCLE_PLATFORM_HINTS: tuple[str, ...] = (
    "YICHUN",
    "XIANGYANG",
    "FUZHOU",
)

_cached_ipmitool_path: Optional[str] = None


def bundled_dir() -> Optional[str]:
    """PyInstaller extraction dir (_internal) when frozen; None in development."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return None


def resource_candidates(*relative_parts: str) -> list[str]:
    """Search paths: exe directory first (user override), then bundled _internal."""
    rel = os.path.join(*relative_parts)
    paths = [os.path.join(BASE_DIR, rel)]
    bundled = bundled_dir()
    if bundled:
        paths.append(os.path.join(bundled, rel))
    return paths


def ipmitool_candidate_paths() -> list[str]:
    """Ordered search paths for ipmitool.exe (first match wins)."""
    candidates: list[str] = []
    env_override = os.environ.get("FRUTOOL_IPMITOOL", "").strip()
    if env_override:
        candidates.append(env_override)
    candidates.extend(resource_candidates(IPMITOOL_DIR_NAME, IPMITOOL_EXE_NAME))
    candidates.append(os.path.join(BASE_DIR, IPMITOOL_EXE_NAME))
    bundled = bundled_dir()
    if bundled:
        candidates.append(os.path.join(bundled, IPMITOOL_EXE_NAME))
    return candidates


def resolve_pcie_eeprom_tool() -> str:
    """Resolved topology script path (ipmitool/ first, then exe root, then bundled)."""
    tools = list_pcie_eeprom_tools()
    if tools:
        return str(tools[0]["path"])
    search_groups = (
        resource_candidates(IPMITOOL_DIR_NAME, PCIE_EEPROM_TOOL_NAME),
        resource_candidates(PCIE_EEPROM_TOOL_NAME),
    )
    for group in search_groups:
        for path in group:
            if os.path.isfile(path):
                return os.path.normpath(path)
    return os.path.normpath(os.path.join(BASE_DIR, PCIE_EEPROM_TOOL_NAME))


def _pcie_script_search_dirs() -> list[str]:
    """Directories to scan for PcieEEpromTool*.py (exe override first, then bundled)."""
    dirs: list[str] = []
    seen: set[str] = set()
    for path in (
        *resource_candidates(IPMITOOL_DIR_NAME),
        BASE_DIR,
        *( [bundled_dir()] if bundled_dir() else [] ),
    ):
        if not path:
            continue
        norm = os.path.normpath(path)
        if os.path.isdir(norm) and norm not in seen:
            seen.add(norm)
            dirs.append(norm)
    return dirs


def _pcie_script_location_label(script_dir: str) -> str:
    norm = os.path.normpath(script_dir)
    base = os.path.normpath(BASE_DIR)
    bundled = bundled_dir()
    if os.path.basename(norm).casefold() == IPMITOOL_DIR_NAME.casefold():
        if bundled and norm.startswith(os.path.normpath(bundled)):
            return "内置 ipmitool/"
        return "ipmitool/"
    if norm == base:
        return "根目录"
    if bundled and norm == os.path.normpath(bundled):
        return "内置根目录"
    return os.path.basename(norm) or "其它"


def list_pcie_eeprom_tools() -> list[dict[str, str]]:
    """Scan for PcieEEpromTool*.py; standard name first, then alphabetical."""
    found: dict[str, dict[str, str]] = {}
    for directory in _pcie_script_search_dirs():
        pattern = os.path.join(directory, PCIE_EEPROM_TOOL_GLOB)
        for match in glob.glob(pattern):
            if not os.path.isfile(match):
                continue
            path = os.path.normpath(os.path.abspath(match))
            if path in found:
                continue
            name = os.path.basename(path)
            loc = _pcie_script_location_label(os.path.dirname(path))
            found[path] = {
                "id": path,
                "label": f"{name} · {loc}",
                "path": path,
                "name": name,
            }

    def sort_key(item: dict[str, str]) -> tuple:
        name = item["name"]
        path = item["path"]
        exact = 0 if name == PCIE_EEPROM_TOOL_NAME else 1
        in_base = 0 if path.startswith(os.path.normpath(BASE_DIR) + os.sep) or path == os.path.normpath(BASE_DIR) else 1
        return (exact, in_base, name.casefold(), path.casefold())

    return sorted(found.values(), key=sort_key)


def load_topo_script_pref() -> str:
    """Last selected topology script path, or empty."""
    try:
        with open(TOPO_SCRIPT_PREF_JSON, encoding="utf-8") as fh:
            data = json.load(fh)
        path = str(data.get("script_path", "")).strip()
        return os.path.normpath(path) if path else ""
    except (OSError, ValueError, TypeError):
        return ""


def save_topo_script_pref(script_path: str) -> None:
    """Persist selected topology script path."""
    path = os.path.normpath(script_path.strip()) if script_path.strip() else ""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(TOPO_SCRIPT_PREF_JSON, "w", encoding="utf-8") as fh:
            json.dump({"script_path": path}, fh, ensure_ascii=False, indent=2)
    except OSError:
        pass


def resolve_pcle_dirs() -> list[str]:
    """PCLE archive directories (exe-side override first, then bundled _internal)."""
    dirs: list[str] = []
    seen: set[str] = set()
    for path in resource_candidates(PCLE_DIR_NAME):
        norm = os.path.normpath(path)
        if os.path.isdir(norm) and norm not in seen:
            seen.add(norm)
            dirs.append(norm)
    return dirs


# Default hint path; call resolve_pcie_eeprom_tool() for actual lookup.
PCIE_EEPROM_TOOL = os.path.join(BASE_DIR, PCIE_EEPROM_TOOL_NAME)


def resolve_ipmitool_path(*, refresh: bool = False) -> Optional[str]:
    """Locate ipmitool.exe under BASE_DIR or FRUTOOL_IPMITOOL env override."""
    global _cached_ipmitool_path
    if not refresh and _cached_ipmitool_path and os.path.isfile(_cached_ipmitool_path):
        return _cached_ipmitool_path
    for path in ipmitool_candidate_paths():
        if path and os.path.isfile(path):
            _cached_ipmitool_path = os.path.normpath(path)
            return _cached_ipmitool_path
    which = shutil.which(IPMITOOL_EXE_NAME)
    if which and os.path.isfile(which):
        _cached_ipmitool_path = os.path.normpath(which)
        return _cached_ipmitool_path
    _cached_ipmitool_path = None
    return None


def get_ipmitool_path() -> str:
    """Resolved ipmitool.exe path, or the preferred default if not found."""
    return resolve_ipmitool_path() or os.path.join(BASE_DIR, IPMITOOL_DIR_NAME, IPMITOOL_EXE_NAME)


def get_ipmitool_dir() -> str:
    """Directory containing ipmitool.exe and its companion files (for PATH / DLL load)."""
    resolved = resolve_ipmitool_path()
    if resolved:
        return os.path.dirname(resolved)
    return os.path.join(BASE_DIR, IPMITOOL_DIR_NAME)


def ipmitool_install_hint() -> str:
    """Human-readable hint listing expected install locations."""
    lines = ["请将 ipmitool 及其依赖文件放入以下任一位置："]
    for path in ipmitool_candidate_paths():
        if path.startswith(BASE_DIR):
            lines.append(f"  • {path}")
        elif bundled_dir() and path.startswith(bundled_dir() or ""):
            lines.append(f"  • {path}  (打包内置)")
        else:
            lines.append(f"  • {path}  (FRUTOOL_IPMITOOL)")
    lines.append(f"  • 或确保 {IPMITOOL_EXE_NAME} 在系统 PATH 中")
    lines.append(f"  • 打包版可在 FRUTool.exe 同目录放置 ipmitool/ 覆盖内置版本")
    return "\n".join(lines)


# Backward-compatible alias (resolved at import; call resolve_ipmitool_path() for fresh lookup)
IPMITOOL = get_ipmitool_path()


def resolve_app_icon_path() -> Optional[str]:
    candidates = [os.path.join(BASE_DIR, APP_ICON_NAME)]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, APP_ICON_NAME))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


from frutool import __version__

APP_PRODUCT_NAME = "FRU 自动化工具"
APP_DESCRIPTION = "FRU 硬件信息自动化配置与备份工具"
APP_COMPANY = "CP Studio"
APP_COPYRIGHT = "Copyright (c) 2026 CP Studio. All rights reserved."
APP_VERSION = __version__
APP_VERSION_LABEL = f"v{__version__}"

NIC_IP_BACKUP_JSON = os.path.join(BACKUP_DIR, "nic_ip_backup.json")
SWAP_SESSION_JSON = os.path.join(BACKUP_DIR, "swap_session.json")
SWAP_NEW_BOARD_TIMEOUT_S = 7200
SWAP_POLL_INTERVAL_MS = 3000
SWAP_POLL_JOB_TIMEOUT_S = 45
SWAP_OFFLINE_STREAK = 3
SWAP_SN_CONFIRM_TIMEOUT_S = 60
SWAP_WAIT_NEW_HEARTBEAT_S = 300


def init_runtime_dirs() -> None:
    """Create runtime data directories (call once at application startup)."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(TOPO_CACHE_DIR, exist_ok=True)


FRU_FIELDS = [
    ("Chassis Part Number", "c", "0", "Chassis"),
    ("Chassis Serial", "c", "1", "Chassis"),
    ("Board Mfg", "b", "0", "Board"),
    ("Board Product", "b", "1", "Board"),
    ("Board Serial", "b", "2", "Board"),
    ("Board Part Number", "b", "3", "Board"),
    ("Product Manufacturer", "p", "0", "Product"),
    ("Product Name", "p", "1", "Product"),
    ("Product Part Number", "p", "2", "Product"),
    ("Product Version", "p", "3", "Product"),
    ("Product Serial", "p", "4", "Product"),
    ("Product Asset Tag", "p", "5", "Product"),
    ("Product Extra", "p", "7", "Product"),
]

LogCallback = Callable[[str, str], None]
LINK_POLL_INTERVAL_MS = 2000
NETWORK_STARTUP_DELAY_MS = 800
NETWORK_STARTUP_RETRY_MS = 2000
NETWORK_STARTUP_MAX_ATTEMPTS = 3
NETWORK_ENUM_JOB_TIMEOUT_S = 15
NETWORK_ENUM_POWERSHELL_TIMEOUT_S = 8
NETWORK_ENUM_IPCONFIG_TIMEOUT_S = 3
NETWORK_ENUM_POWERSHELL_PROBE_TIMEOUT_S = 3
BMC_PING_INTERVAL_S = 1.5
BMC_PING_TIMEOUT_MS = 800
BMC_PROBE_JOIN_TIMEOUT_S = 2.0
NETWORK_CHANGE_DEBOUNCE_MS = 300
RESIZE_DEBOUNCE_MS = 100
DHCP_JOIN_TIMEOUT_S = 2.0
