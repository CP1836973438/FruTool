"""IPMI tool integration and FRU parsing."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional

from frutool.config import LogCallback, get_ipmitool_dir, get_ipmitool_path, resolve_ipmitool_path
from frutool.infrastructure.network import _startup_flags, _valid_ipv4

def mask_ipmi_args(args: list[str]) -> list[str]:
    masked = list(args)
    for i, arg in enumerate(masked[:-1]):
        if arg == "-P":
            masked[i + 1] = "******"
    return masked


def _subprocess_env_with_tools() -> dict[str, str]:
    env = os.environ.copy()
    path = env.get("PATH", "")
    parts = path.split(os.pathsep) if path else []
    ipmi_dir = get_ipmitool_dir()
    if ipmi_dir and ipmi_dir not in parts:
        parts.insert(0, ipmi_dir)
    env["PATH"] = os.pathsep.join(parts)
    return env


def _frozen_python_argv_candidates() -> list[list[str]]:
    """Ordered Python launch candidates for frozen (packaged) builds."""
    seen: set[tuple[str, ...]] = set()
    candidates: list[list[str]] = []

    def add(argv: list[str]) -> None:
        key = tuple(argv)
        if key not in seen:
            seen.add(key)
            candidates.append(argv)

    py_launcher = shutil.which("py")
    if py_launcher:
        add([py_launcher, "-3"])

    for name in ("python3", "python"):
        found = shutil.which(name)
        if found and os.path.isfile(found):
            add([found])

    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["where", "python"],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=5,
                creationflags=_startup_flags(),
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    path = line.strip()
                    if path and os.path.isfile(path):
                        add([path])
        except Exception:
            pass

    return candidates


def _probe_python_argv(argv: list[str]) -> bool:
    try:
        result = subprocess.run(
            [*argv, "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
            creationflags=_startup_flags(),
        )
        return result.returncode == 0
    except Exception:
        return False


def script_python_argv(log_cb: Optional[LogCallback] = None) -> Optional[list[str]]:
    """Argv prefix for running topology scripts in development or frozen builds."""
    if not getattr(sys, "frozen", False):
        return [sys.executable]

    for argv in _frozen_python_argv_candidates():
        if _probe_python_argv(argv):
            return argv

    if log_cb:
        log_cb(
            "error",
            "Python not found or not runnable from this app. In the same terminal run "
            "'python --version' and 'py -3 --version'; if both work, restart FRUTool "
            "after install or log off/on so the GUI inherits PATH.",
        )
    return None


def resolve_script_python(log_cb: Optional[LogCallback] = None) -> Optional[str]:
    """First token of script_python_argv (for presence checks)."""
    argv = script_python_argv(log_cb)
    return argv[0] if argv else None

def run_ipmi(args_list: list[str], log_cb: Optional[LogCallback] = None, timeout: int = 30):
    ipmitool = resolve_ipmitool_path(refresh=True) or get_ipmitool_path()
    cmd = [ipmitool] + args_list
    if log_cb:
        log_cb("cmd", " ".join(mask_ipmi_args(cmd)))
    if not os.path.isfile(ipmitool):
        if log_cb:
            log_cb("error", f"ipmitool.exe not found: {ipmitool}")
        return -1, "", "not found"
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            creationflags=_startup_flags(),
            env=_subprocess_env_with_tools(),
            cwd=get_ipmitool_dir(),
        )
        if result.stdout.strip() and log_cb:
            log_cb("info", result.stdout.strip())
        if result.stderr.strip() and log_cb:
            log_cb("warning", result.stderr.strip())
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        if log_cb:
            log_cb("error", f"Command timed out after {timeout}s")
        return -1, "", "timeout"
    except FileNotFoundError:
        if log_cb:
            log_cb("error", f"ipmitool.exe not found: {ipmitool}")
        return -1, "", "not found"
    except Exception as exc:
        if log_cb:
            log_cb("error", f"Command failed: {exc}")
        return -1, "", str(exc)


def ipmi_base_args(user: str, pwd: str, bmc_ip: str) -> list[str]:
    return ["-I", "lanplus", "-H", bmc_ip, "-U", user, "-P", pwd]


def wait_for_bmc(user: str, pwd: str, bmc_ip: str, log_cb: LogCallback, max_wait: int = 180) -> bool:
    log_cb("info", f"Waiting for BMC {bmc_ip} (fru list / Board Serial), timeout {max_wait}s")
    deadline = time.time() + max_wait
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "list", "0"], None, 20)
        serial = parse_board_serial(out) if rc == 0 else None
        if serial:
            log_cb("success", f"BMC FRU ready (Board Serial: {serial}), attempt {attempt}")
            return True
        log_cb("info", f"Probe {attempt}: FRU not ready, retrying in 5s")
        time.sleep(5)
    log_cb("error", "BMC FRU wait timed out")
    return False


def probe_bmc_ping(bmc_ip: str, timeout_ms: int = 1000) -> bool:
    if not bmc_ip or not _valid_ipv4(bmc_ip):
        return False
    if sys.platform == "win32":
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), bmc_ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), bmc_ip]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=max(2, timeout_ms // 1000 + 2),
            creationflags=_startup_flags(),
        )
        return result.returncode == 0
    except Exception:
        return False


def parse_board_serial(fru_output: str) -> Optional[str]:
    for line in fru_output.splitlines():
        match = re.search(r"Board Serial\s*:\s*(.+)", line)
        if match:
            value = match.group(1).strip()
            return value or None
    return None


def parse_fru_field(fru_output: str, field_name: str) -> Optional[str]:
    for line in fru_output.splitlines():
        match = re.search(rf"{re.escape(field_name)}\s*:\s*(.+)", line)
        if match:
            value = match.group(1).strip()
            return value or None
    return None


def parse_product_serial(fru_output: str) -> Optional[str]:
    return parse_fru_field(fru_output, "Product Serial")


@dataclass
class FruFingerprint:
    board_serial: str
    product_serial: str
    product_name: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "board_serial": self.board_serial,
            "product_serial": self.product_serial,
            "product_name": self.product_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FruFingerprint:
        return cls(
            board_serial=str(data.get("board_serial", "")),
            product_serial=str(data.get("product_serial", "")),
            product_name=str(data.get("product_name", "")),
        )


def capture_fru_fingerprint(fru_output: str) -> Optional[FruFingerprint]:
    board_serial = parse_board_serial(fru_output)
    if not board_serial:
        return None
    return FruFingerprint(
        board_serial=board_serial,
        product_serial=parse_product_serial(fru_output) or "",
        product_name=parse_fru_field(fru_output, "Product Name") or "",
    )


def probe_fru_list(user: str, pwd: str, bmc_ip: str) -> tuple[bool, str]:
    if not user or not pwd or not bmc_ip:
        return False, ""
    rc, out, _ = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "list", "0"], None, 20)
    if rc != 0:
        return False, ""
    return True, out


def log_fru_print(user: str, pwd: str, bmc_ip: str, log: LogCallback, *, title: str) -> None:
    log("info", title)
    rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "print", "0"], log, 30)
    if rc != 0:
        log("warning", "fru print 0 failed")

