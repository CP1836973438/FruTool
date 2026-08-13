"""PCIe topology EEPROM write via PcieEEpromTool."""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional

from frutool.config import BASE_DIR, LogCallback, get_ipmitool_dir, resolve_pcie_eeprom_tool
from frutool.domain.ipmi import (
    _subprocess_env_with_tools,
    mask_ipmi_args,
    script_python_argv,
)
from frutool.infrastructure.network import _startup_flags

def run_pcie_topology_write(bin_path: str, user: str, pwd: str, bmc_ip: str, log_cb: LogCallback) -> bool:
    topo_script = resolve_pcie_eeprom_tool()
    if not os.path.isfile(topo_script):
        log_cb("error", f"PcieEEpromTool.py not found: {topo_script}")
        return False
    if not os.path.isfile(bin_path):
        log_cb("error", f"Topology file not found: {bin_path}")
        return False
    size = os.path.getsize(bin_path)
    if size > 512:
        log_cb("error", f"Topology file is larger than 512 bytes: {size}")
        return False
    python_argv = script_python_argv(log_cb)
    if not python_argv:
        return False
    cmd = [
        *python_argv,
        topo_script,
        "-H",
        bmc_ip,
        "-U",
        user,
        "-P",
        pwd,
        "-I",
        "lanplus",
        "-W",
        bin_path,
    ]
    work_dir = get_ipmitool_dir() or BASE_DIR
    log_cb("cmd", " ".join(mask_ipmi_args(cmd)))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=120,
            cwd=work_dir,
            env=_subprocess_env_with_tools(),
            creationflags=_startup_flags(),
        )
        for line in (result.stdout or "").splitlines():
            if line.strip():
                log_cb("info", line.strip())
        for line in (result.stderr or "").splitlines():
            if line.strip():
                log_cb("warning", line.strip())
        if result.returncode == 0:
            log_cb("success", "Topology file write completed (PcieEEpromTool)")
            return True
        log_cb("error", f"PcieEEpromTool exited with code {result.returncode}")
        return False
    except subprocess.TimeoutExpired:
        log_cb("error", "PcieEEpromTool timed out after 120s")
        return False
    except FileNotFoundError:
        log_cb("error", f"Python interpreter not found: {python_argv[0]}")
        return False
    except Exception as exc:
        log_cb("error", f"PcieEEpromTool failed: {exc}")
        return False

