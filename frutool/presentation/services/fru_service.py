"""FRU batch write validation and worker job (no Qt)."""
from __future__ import annotations

import time
from typing import Optional

from frutool.config import FRU_FIELDS, LogCallback
from frutool.domain.ipmi import ipmi_base_args, parse_fru_field, probe_fru_list, run_ipmi

DialogError = tuple[str, str, str]  # title, message, kind ("warning" | "critical")


def _resolve_fru_access(
    bmc_ip: str,
    new_user: str,
    new_pwd: str,
    old_user: str,
    old_pwd: str,
) -> Optional[tuple[str, str, str]]:
    if not bmc_ip:
        return None
    new_user = new_user.strip()
    old_user = old_user.strip()
    if new_user and new_pwd:
        ok, out = probe_fru_list(new_user, new_pwd, bmc_ip)
        if ok:
            return new_user, new_pwd, out
    if old_user and old_pwd:
        ok, out = probe_fru_list(old_user, old_pwd, bmc_ip)
        if ok:
            return old_user, old_pwd, out
    return None


def resolve_fru_credentials(
    bmc_ip: str,
    new_user: str,
    new_pwd: str,
    old_user: str,
    old_pwd: str,
    log: LogCallback | None = None,
) -> Optional[tuple[str, str]]:
    access = _resolve_fru_access(bmc_ip, new_user, new_pwd, old_user, old_pwd)
    if not access:
        if log:
            log("warning", "FRU credential resolve failed (new and old board)")
        return None
    user, pwd, _out = access
    return user, pwd


def run_fru_hint_read(
    bmc_ip: str,
    new_user: str,
    new_pwd: str,
    old_user: str,
    old_pwd: str,
    log: LogCallback | None = None,
) -> dict[str, str]:
    access = _resolve_fru_access(bmc_ip, new_user, new_pwd, old_user, old_pwd)
    if not access:
        if log:
            log("warning", "FRU hint read failed (new and old board credentials)")
        return {}
    _user, _pwd, out = access
    return {name: parse_fru_field(out, name) or "" for name, _area, _idx, _group in FRU_FIELDS}


def validate_fru_batch_write(
    new_user: str,
    new_pwd: str,
    old_user: str,
    old_pwd: str,
    fields: list[tuple[str, str, str]],
) -> Optional[DialogError]:
    new_ok = bool(new_user.strip() and new_pwd)
    old_ok = bool(old_user.strip() and old_pwd)
    if not new_ok and not old_ok:
        return (
            "信息不完整",
            "请在连接设置中填写新板或旧板的 BMC 账号和密码。",
            "warning",
        )
    if not fields:
        return ("无内容", "请至少填写一个 FRU 字段值。", "warning")
    return None


def run_fru_batch_write(
    user: str,
    pwd: str,
    bmc_ip: str,
    fields: list[tuple[str, str, str]],
    log: LogCallback,
) -> dict[str, int]:
    success = 0
    for area, idx, value in fields:
        rc, _out, _err = run_ipmi(
            ipmi_base_args(user, pwd, bmc_ip) + ["fru", "edit", "0", "field", area, idx, value],
            log,
            20,
        )
        if rc == 0:
            success += 1
            log("success", f"field {area} {idx} written")
        else:
            log("error", f"field {area} {idx} failed")
        time.sleep(0.5)
    return {"success": success, "total": len(fields)}


def run_fru_batch_write_resolved(
    bmc_ip: str,
    new_user: str,
    new_pwd: str,
    old_user: str,
    old_pwd: str,
    fields: list[tuple[str, str, str]],
    log: LogCallback,
) -> dict[str, object]:
    access = _resolve_fru_access(bmc_ip, new_user, new_pwd, old_user, old_pwd)
    if not access:
        log("warning", "FRU batch write: credential resolve failed")
        return {"ok": False, "cred_failed": True}
    user, pwd, _out = access
    result = run_fru_batch_write(user, pwd, bmc_ip, fields, log)
    result["ok"] = True
    return result


def summarize_fru_batch_result(result: object) -> tuple[str, str, str]:
    data = result if isinstance(result, dict) else {"success": 0, "total": 0}
    if data.get("cred_failed"):
        return (
            "warning",
            "FRU 批量刷写已中止：BMC 凭据无效",
            "BMC 凭据验证失败，请检查连接设置。",
        )
    success = int(data.get("success", 0))
    total = int(data.get("total", 0))
    level = "success" if success == total else "warning"
    log_line = f"批量刷写完成: {success}/{total}"
    dialog = f"FRU 批量刷写完成: {success}/{total}"
    return level, log_line, dialog
