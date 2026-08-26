"""PCIe topology write validation and worker job (no Qt)."""

from __future__ import annotations

import os
from typing import Optional

from frutool.config import LogCallback, resolve_pcie_eeprom_tool
from frutool.demo import hardware_sim_enabled
from frutool.domain.topo_catalog import (
    canonical_manufacturer,
    extract_catalog_entry,
    match_topo_candidates,
    parse_suite_code,
)
from frutool.domain.ipmi import resolve_script_python
from frutool.domain.pcie_topo import run_pcie_topology_write

DialogError = tuple[str, str, str]


def validate_topo_write(
    path: str,
    user: str,
    pwd: str,
    script_path: Optional[str] = None,
) -> Optional[DialogError]:
    trimmed = path.strip()
    if not trimmed:
        return ("未选择文件", "请选择拓扑 .bin 文件。", "warning")
    if not os.path.exists(trimmed):
        return ("文件不存在", f"找不到文件: {trimmed}", "critical")
    if not user or not pwd:
        return (
            "信息不完整",
            "请在连接设置中填写新板 BMC 账号和密码。",
            "warning",
        )
    topo_script = (script_path or "").strip() or resolve_pcie_eeprom_tool()
    if not os.path.isfile(topo_script):
        return ("脚本不存在", f"找不到拓扑脚本:\n{topo_script}", "critical")
    if not hardware_sim_enabled() and not resolve_script_python():
        return (
            "未找到 Python",
            "请确认终端中 python --version 或 py -3 --version 可用；"
            "若终端可用但工具内失败，请注销或重启后再试（让 GUI 继承 PATH）。",
            "critical",
        )
    return None


def run_topo_write(
    path: str,
    user: str,
    pwd: str,
    bmc_ip: str,
    log: LogCallback,
    script_path: Optional[str] = None,
) -> dict[str, bool]:
    return {
        "ok": run_pcie_topology_write(
            path.strip(), user, pwd, bmc_ip, log, script_path=script_path
        )
    }


def run_topo_preload(
    product_extra_hint: str,
    product_manufacturer_hint: str,
    log: LogCallback,
) -> dict[str, object]:
    suite = parse_suite_code(product_extra_hint)
    if not suite:
        return {
            "ok": False,
            "path": "",
            "suite": "",
            "manufacturer": (product_manufacturer_hint or "").strip(),
            "candidates": [],
            "catalog": [],
            "message": "未能从新板 FRU 读取套餐号（Product Extra）。",
        }
    return match_topo_candidates(
        suite,
        canonical_manufacturer((product_manufacturer_hint or "").strip()),
        log=log,
    )


def run_topo_catalog_pick(entry_id: str, log: LogCallback) -> dict[str, object]:
    return extract_catalog_entry(entry_id, log=log)
