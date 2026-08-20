"""Swap skip-step-1 demo — fake BMC online + a manual FRU bin without timestamp."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from frutool.config import BACKUP_DIR, init_runtime_dirs
from frutool.demo import DEMO_SKIP_SN, swap_demo_enabled
from frutool.infrastructure.network import NetworkConfig

if TYPE_CHECKING:
    from frutool.presentation.app import ApplicationRoot


def seed_demo_backup(sn: str = DEMO_SKIP_SN) -> str:
    """Write `{sn}_manual.bin` into fru_backup so step 1 can be skipped."""
    init_runtime_dirs()
    path = os.path.join(BACKUP_DIR, f"{sn}.bin")
    if not os.path.isfile(path):
        with open(path, "wb") as fh:
            fh.write(b"FRUTOOL_DEMO_FRU_BIN\n")
    return path


def apply_swap_demo(app_root: ApplicationRoot) -> str:
    bin_path = seed_demo_backup()
    network = app_root.conn.network
    network.apply_bmc_state_from_result({"bmc_online": True})
    network._local_online = True  # noqa: SLF001 — demo-only fake link state
    network.localOnlineChanged.emit()
    cfg = network.network_config
    network.network_config = NetworkConfig(
        local_ip=cfg.local_ip or "192.168.1.2",
        bmc_ip=cfg.bmc_ip or "192.168.1.100",
        subnet_mask=cfg.subnet_mask or "255.255.255.0",
        prefix_length=cfg.prefix_length or 24,
        interface_label="Demo",
    )
    network.bmcIpChanged.emit()
    network.localIpChanged.emit()
    network._network_summary = "演示模式 · BMC 192.168.1.100（模拟在线）"
    network.networkSummaryChanged.emit()

    app_root.chrome.showPage("main")
    app_root.controller.host.log(
        "info",
        f"换板演示：BMC 已模拟在线。备份文件 {os.path.basename(bin_path)} "
        f"已放在 fru_backup（对应 SN {DEMO_SKIP_SN}）。请自行填写 SN 验证是否跳过步骤 1。",
    )
    return bin_path


def schedule_swap_demo(app_root: ApplicationRoot) -> None:
    from PyQt6.QtCore import QTimer

    def _run() -> None:
        if not swap_demo_enabled():
            return
        try:
            apply_swap_demo(app_root)
        except Exception as exc:
            app_root.controller.host.log("critical", f"换板演示初始化失败: {exc}")

    QTimer.singleShot(350, _run)
