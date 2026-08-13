"""Manual IPMI command parsing and execution (no Qt)."""
from __future__ import annotations

import os
import shlex
from typing import Optional

from frutool.config import LogCallback
from frutool.domain.ipmi import ipmi_base_args, run_ipmi

DialogError = tuple[str, str, str]


def parse_ipmi_args(cmd_str: str) -> tuple[Optional[list[str]], Optional[DialogError]]:
    try:
        return shlex.split(cmd_str, posix=False), None
    except ValueError as exc:
        return None, ("解析失败", str(exc), "warning")


def is_shell_ipmi_command(cmd_str: str) -> bool:
    """True when a free-mode shell line invokes ipmitool."""
    trimmed = cmd_str.strip()
    if not trimmed:
        return False
    try:
        parts = shlex.split(trimmed, posix=False)
    except ValueError:
        return False
    if not parts:
        return False
    exe = os.path.basename(parts[0]).lower()
    return exe in ("ipmitool", "ipmitool.exe")


def run_ipmi_command(
    cmd_str: str,
    user: str,
    pwd: str,
    bmc_ip: str,
    log: LogCallback,
    *,
    timeout_s: int = 30,
) -> dict[str, bool]:
    extra_args, err = parse_ipmi_args(cmd_str)
    if err is not None or extra_args is None:
        raise ValueError(err[1] if err else "Invalid command")
    rc, _out, _err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + extra_args, log, timeout_s)
    return {"ok": rc == 0}
