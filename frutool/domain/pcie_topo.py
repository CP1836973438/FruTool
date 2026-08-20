"""PCIe topology EEPROM write via PcieEEpromTool."""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional

from frutool.config import BASE_DIR, LogCallback, get_ipmitool_dir, resolve_pcie_eeprom_tool
from frutool.domain.ipmi import (
    _subprocess_env_with_tools,
    mask_ipmi_args,
    script_python_argv,
)
from frutool.infrastructure.network import _startup_flags

# Staged copy name under ipmitool/ — avoids overwriting the primary script.
STAGED_TOPO_SCRIPT_NAME = "PcieEEpromTool_run.py"


def stage_topo_script_for_run(script_path: str, log_cb: Optional[LogCallback] = None) -> Optional[str]:
    """Ensure the topology script lives under ipmitool/ before execution.

    Field constraint: absolute paths outside ipmitool/ fail; only scripts in that
    directory run reliably. If the selected file is already there, use it as-is;
    otherwise copy to ``PcieEEpromTool_run.py`` inside ipmitool/.
    """
    src = os.path.normpath(os.path.abspath(script_path.strip()))
    if not os.path.isfile(src):
        if log_cb:
            log_cb("error", f"Topology script not found: {src}")
        return None
    work_dir = os.path.normpath(get_ipmitool_dir() or os.path.join(BASE_DIR, "ipmitool"))
    try:
        os.makedirs(work_dir, exist_ok=True)
    except OSError as exc:
        if log_cb:
            log_cb("error", f"Cannot create ipmitool dir: {work_dir} ({exc})")
        return None
    if os.path.normpath(os.path.dirname(src)) == work_dir:
        return src
    dest = os.path.join(work_dir, STAGED_TOPO_SCRIPT_NAME)
    try:
        shutil.copy2(src, dest)
    except OSError as exc:
        if log_cb:
            log_cb("error", f"Failed to load script into ipmitool/: {exc}")
        return None
    if log_cb:
        log_cb("info", f"Loaded topology script into ipmitool/: {os.path.basename(src)} → {STAGED_TOPO_SCRIPT_NAME}")
    return os.path.normpath(dest)


def run_pcie_topology_write(
    bin_path: str,
    user: str,
    pwd: str,
    bmc_ip: str,
    log_cb: LogCallback,
    script_path: Optional[str] = None,
) -> bool:
    topo_script = (script_path or "").strip() or resolve_pcie_eeprom_tool()
    if not os.path.isfile(topo_script):
        log_cb("error", f"Topology script not found: {topo_script}")
        return False
    staged = stage_topo_script_for_run(topo_script, log_cb)
    if not staged:
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
    work_dir = os.path.dirname(staged)
    cmd = [
        *python_argv,
        staged,
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
