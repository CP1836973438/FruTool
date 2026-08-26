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
    parse_board_part_number,
    parse_board_serial,
    probe_fru_list,
    run_ipmi,
    wait_for_bmc,
)


def _norm_board_pn(value: str) -> str:
    return (value or "").strip().casefold()


def should_restore_new_board_pn(new_pn: str, old_pn: str) -> bool:
    """Restore new-board Board Part Number when it is present and differs from the old board."""
    new = (new_pn or "").strip()
    if not new:
        return False
    return _norm_board_pn(new) != _norm_board_pn(old_pn)


def clone_restore_summary(result: dict) -> str:
    serial = str(result.get("serial") or "—")
    pn = str(result.get("part_number") or "").strip() or "—"
    if result.get("pn_restored"):
        return (
            "FRU 克隆完成。新旧主板 PN 不一致，已还原新板 Board Serial，并写回新板 Board Part Number。\n"
            f"Board Serial: {serial}\nBoard Part Number: {pn}"
        )
    return (
        "FRU 克隆完成。主板 PN 一致，仅还原新板 Board Serial。\n"
        f"Board Serial: {serial}"
    )


def _fru_edit_field(
    user: str,
    pwd: str,
    bmc_ip: str,
    area: str,
    index: str,
    value: str,
    log: LogCallback,
) -> int:
    rc, _out, _err = run_ipmi(
        ipmi_base_args(user, pwd, bmc_ip) + ["fru", "edit", "0", "field", area, index, value],
        log,
        20,
    )
    return rc


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
    if os.environ.get("FRUTOOL_DEMO_SWAP") == "1" or os.environ.get("FRUTOOL_DEMO_ALL") == "1":
        from frutool.demo.full_demo import seed_demo_fru_backup

        src = seed_demo_fru_backup()
        if not bin_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            bin_path = os.path.join(BACKUP_DIR, f"{sn}_{ts}.bin")
        try:
            import shutil

            shutil.copy2(src, bin_path)
        except OSError:
            with open(bin_path, "wb") as fh:
                fh.write(b"FRUTOOL_DEMO_FRU_EXPORT\n")
        log("success", f"[演示] FRU backup saved: {bin_path}")
        return {"ok": True, "bmc_online": True, "bin_path": bin_path}
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
    if os.environ.get("FRUTOOL_DEMO_SWAP") == "1" or os.environ.get("FRUTOOL_DEMO_ALL") == "1":
        log("success", "演示模式：跳过真实 BMC 写入，模拟克隆成功")
        return {
            "ok": True,
            "bmc_online": True,
            "serial": "DEMO-BOARD-001",
            "part_number": "",
            "pn_restored": False,
            "rollback": "",
        }
    if not wait_for_bmc(user, pwd, bmc_ip, log):
        return {"ok": False, "bmc_online": False, "title": "超时", "message": "新板 BMC 长时间无响应。"}
    rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "list", "0"], log, 20)
    if rc != 0:
        return {"ok": False, "bmc_online": True, "title": "读取失败", "message": "无法读取新板 FRU。"}
    serial = parse_board_serial(out)
    if not serial:
        return {"ok": False, "bmc_online": True, "title": "解析失败", "message": "无法从 fru list 解析 Board Serial。"}
    new_pn = parse_board_part_number(out) or ""
    log("success", f"New board Board Serial saved: {serial}")
    if new_pn:
        log("info", f"New board Board Part Number saved: {new_pn}")
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    rollback = os.path.join(BACKUP_DIR, f"{sn}_NEW_ORIGINAL_{ts}.bin")
    rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "read", "0", rollback], log, 60)
    if rc != 0 or not os.path.exists(rollback):
        rollback = ""
        log("warning", "New board original FRU backup failed; rollback will be unavailable")
    rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "write", "0", old_bin_path], log, 60)
    if rc != 0:
        return {"ok": False, "bmc_online": True, "title": "写入失败", "message": "FRU 克隆写入失败。"}
    rc, out, err = run_ipmi(ipmi_base_args(user, pwd, bmc_ip) + ["fru", "list", "0"], log, 20)
    old_pn = parse_board_part_number(out) or "" if rc == 0 else ""
    if rc != 0:
        log("warning", "克隆后无法再读 FRU，无法确认旧板 PN；若新板有 PN 将写回")
    if _fru_edit_field(user, pwd, bmc_ip, "b", "2", serial, log) != 0:
        log("error", f"Manual command: fru edit 0 field b 2 {serial}")
        return {"ok": False, "bmc_online": True, "title": "还原失败", "message": f"Board Serial 还原失败，真实 SN: {serial}"}
    pn_restored = False
    if should_restore_new_board_pn(new_pn, old_pn):
        log("info", f"主板 PN 不一致（旧 {old_pn or '—'} / 新 {new_pn}），写回新板 Board Part Number")
        if _fru_edit_field(user, pwd, bmc_ip, "b", "3", new_pn, log) != 0:
            log("error", f"Manual command: fru edit 0 field b 3 {new_pn}")
            return {
                "ok": False,
                "bmc_online": True,
                "title": "还原失败",
                "message": f"Board Part Number 还原失败，新板 PN: {new_pn}",
            }
        pn_restored = True
        log("success", "FRU clone, Board Serial and Board Part Number restore completed")
    else:
        log("info", "主板 PN 一致，仅还原 Board Serial")
        log("success", "FRU clone and Board Serial restore completed")
    log_fru_print(user, pwd, bmc_ip, log, title="[Verify] New board FRU after clone:")
    return {
        "ok": True,
        "bmc_online": True,
        "serial": serial,
        "part_number": new_pn,
        "pn_restored": pn_restored,
        "rollback": rollback,
    }

