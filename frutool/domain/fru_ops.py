"""FRU export/clone workflow steps."""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Optional

from frutool.config import BACKUP_DIR, LogCallback
from frutool.domain.ipmi import (
    ipmi_base_args,
    log_fru_print,
    parse_board_serial,
    probe_fru_list,
    run_ipmi,
    wait_for_bmc,
)

def run_step1_export(
    sn: str,
    user: str,
    pwd: str,
    bmc_ip: str,
    log: LogCallback,
    *,
    bin_path: Optional[str] = None,
    skip_wait: bool = False,
) -> dict:
    log("info", "-" * 50)
    log("info", f"Step 1 started, SN={sn}")
    if not skip_wait:
        if not wait_for_bmc(user, pwd, bmc_ip, log):
            return {"ok": False, "bmc_online": False, "title": "超时", "message": "BMC 长时间无响应。"}
    else:
        ready = False
        for attempt in range(3):
            ok, out = probe_fru_list(user, pwd, bmc_ip)
            if ok and parse_board_serial(out):
                ready = True
                break
            if attempt < 2:
                log("info", f"IPMI 尚未就绪，3s 后重试 ({attempt + 1}/3)")
                time.sleep(3)
        if not ready:
            return {"ok": False, "bmc_online": False, "title": "超时", "message": "BMC FRU 尚未就绪。"}
    if not bin_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        bin_path = os.path.join(BACKUP_DIR, f"{sn}_{ts}.bin")
    log("info", "Exporting FRU backup")
    rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "read", "0", bin_path], log, 60)
    if rc != 0 or not os.path.exists(bin_path):
        log("error", "FRU export failed")
        return {"ok": False, "bmc_online": True, "title": "失败", "message": "FRU 导出失败，请查看日志。"}
    log("success", f"FRU backup saved: {bin_path} ({os.path.getsize(bin_path)} bytes)")
    log_fru_print(user, pwd, bmc_ip, log, title="[Verify] Old board FRU after export:")
    return {"ok": True, "bmc_online": True, "bin_path": bin_path}


def run_step2_clone(
    sn: str,
    user: str,
    pwd: str,
    bmc_ip: str,
    old_bin_path: str,
    log: LogCallback,
) -> dict:
    log("info", "-" * 50)
    log("info", f"Step 2 started, SN={sn}")
    if not wait_for_bmc(user, pwd, bmc_ip, log):
        return {"ok": False, "bmc_online": False, "title": "超时", "message": "新板 BMC 长时间无响应。"}
    rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "list", "0"], log, 20)
    if rc != 0:
        return {"ok": False, "bmc_online": True, "title": "读取失败", "message": "无法读取新板 FRU。"}
    serial = parse_board_serial(out)
    if not serial:
        return {"ok": False, "bmc_online": True, "title": "解析失败", "message": "无法从 fru list 解析 Board Serial。"}
    log("success", f"New board Board Serial saved: {serial}")
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    rollback = os.path.join(BACKUP_DIR, f"{sn}_NEW_ORIGINAL_{ts}.bin")
    rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "read", "0", rollback], log, 60)
    if rc != 0 or not os.path.exists(rollback):
        rollback = ""
        log("warning", "New board original FRU backup failed; rollback will be unavailable")
    rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "write", "0", old_bin_path], log, 60)
    if rc != 0:
        return {"ok": False, "bmc_online": True, "title": "写入失败", "message": "FRU 克隆写入失败。"}
    rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "edit", "0", "field", "b", "2", serial], log, 20)
    if rc != 0:
        log("error", f"Manual command: fru edit 0 field b 2 {serial}")
        return {"ok": False, "bmc_online": True, "title": "还原失败", "message": f"Board Serial 还原失败，真实 SN: {serial}"}
    log("success", "FRU clone and Board Serial restore completed")
    log_fru_print(user, pwd, bmc_ip, log, title="[Verify] New board FRU after clone:")
    return {"ok": True, "bmc_online": True, "serial": serial, "rollback": rollback}

