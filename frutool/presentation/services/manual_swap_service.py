"""Manual board-swap step validation and worker jobs (no Qt)."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from frutool.config import BACKUP_DIR, LogCallback, ipmitool_install_hint, resolve_ipmitool_path
from frutool.domain.backup import list_fru_backups_for_sn
from frutool.domain.fru_ops import run_step1_export, run_step2_clone
from frutool.domain.ipmi import ipmi_base_args, run_ipmi

DialogError = tuple[str, str, str]


def validate_step1_export(sn: str, user: str, pwd: str) -> Optional[DialogError]:
    if not sn.strip():
        return ("信息不完整", "请输入旧服务器 SN。", "warning")
    if not user or not pwd:
        return ("信息不完整", "请输入旧板 BMC 账号和密码。", "warning")
    from frutool.demo import swap_demo_enabled

    if swap_demo_enabled():
        return None
    if not resolve_ipmitool_path():
        return ("未找到 ipmitool", ipmitool_install_hint(), "critical")
    return None


def plan_step1_bin_path(sn: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return os.path.join(BACKUP_DIR, f"{sn.strip()}_{ts}.bin")


def list_step1_backups(sn: str) -> list[str]:
    return list_fru_backups_for_sn(sn.strip())


def validate_step2_clone(sn: str, user: str, pwd: str) -> Optional[DialogError]:
    if not sn.strip():
        return ("信息不完整", "请输入旧服务器 SN。", "warning")
    if not user or not pwd:
        return ("信息不完整", "请输入新板 BMC 账号和密码。", "warning")
    if not list_fru_backups_for_sn(sn.strip()):
        return (
            "未找到备份",
            f"未找到 SN={sn.strip()} 的 FRU 备份，请先执行步骤 1。",
            "critical",
        )
    return None


def resolve_step2_backup_path(sn: str) -> tuple[Optional[str], Optional[str]]:
    candidates = list_fru_backups_for_sn(sn.strip())
    if not candidates:
        return None, None
    name = candidates[-1]
    return os.path.join(BACKUP_DIR, name), name


def run_step1_job(
    sn: str,
    user: str,
    pwd: str,
    bmc_ip: str,
    bin_path: str,
    log: LogCallback,
    *,
    skip_wait: bool = False,
) -> dict:
    return run_step1_export(
        sn.strip(), user, pwd, bmc_ip, log, bin_path=bin_path, skip_wait=skip_wait
    )


def run_step2_job(
    sn: str,
    user: str,
    pwd: str,
    bmc_ip: str,
    old_bin_path: str,
    log: LogCallback,
) -> dict:
    return run_step2_clone(sn.strip(), user, pwd, bmc_ip, old_bin_path, log)


def validate_rollback(backup_path: Optional[str]) -> Optional[DialogError]:
    if not backup_path:
        return ("无可用备份", "没有可回滚的新板原始 FRU 备份。", "critical")
    return None


def run_rollback(user: str, pwd: str, bmc_ip: str, fru_path: str, log: LogCallback) -> dict[str, bool]:
    rc, _out, _err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "write", "0", fru_path], log, 60)
    return {"ok": rc == 0}
