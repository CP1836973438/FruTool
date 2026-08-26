"""Full UI demo — FRU / swap / topology / DHCP without real BMC."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from frutool.config import BACKUP_DIR, BASE_DIR, FRU_FIELDS, init_runtime_dirs
from frutool.demo import DEMO_ALL_ENV, DEMO_SN, full_demo_enabled
from frutool.infrastructure.network import IPV4_ORIGIN_MANUAL, NetworkChoice, NetworkConfig

if TYPE_CHECKING:
    from frutool.presentation.app import ApplicationRoot

# Parsed from fru_backup/21D111761_20260610_1458.bin (field order / typical IPMI layout)
DEMO_FRU_HINTS: dict[str, str] = {
    "Chassis Part Number": "null",
    "Chassis Serial": "xxxx",
    "Board Mfg": "Inspur",
    "Board Product": "MBQC27K70262A60",
    "Board Serial": "MBQC27K70262A60",
    "Board Part Number": "YZMB-03296-10F",
    "Product Manufacturer": "Inspur",
    "Product Name": "G220-A3",
    "Product Part Number": "xxxx",
    "Product Version": "Intel Whitley IceLake",
    "Product Serial": DEMO_SN,
    "Product Asset Tag": "2024-is-srv-2170918",
    "Product Extra": "Suite:S62D1-I8DD2M-L",
}

DEMO_LOCAL_IP = "192.168.70.2"
DEMO_BMC_IP = "192.168.70.100"
DEMO_SOURCE_BIN = "21D111761_20260610_1458.bin"


def _resolve_source_bin() -> Path | None:
    candidates = [
        Path(BASE_DIR) / "fru_backup" / DEMO_SOURCE_BIN,
        Path(BASE_DIR) / DEMO_SOURCE_BIN,
        Path(__file__).resolve().parents[2] / "fru_backup" / DEMO_SOURCE_BIN,
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def seed_demo_fru_backup() -> str:
    """Place real sample FRU bin into fru_backup for swap skip-step-1 demos."""
    init_runtime_dirs()
    src = _resolve_source_bin()
    dest_plain = Path(BACKUP_DIR) / f"{DEMO_SN}.bin"
    dest_named = Path(BACKUP_DIR) / DEMO_SOURCE_BIN
    if src is not None:
        if not dest_named.exists() or dest_named.resolve() != src.resolve():
            shutil.copy2(src, dest_named)
        shutil.copy2(src, dest_plain)
        return str(dest_plain)
    # Fallback tiny placeholder if sample missing from pack
    if not dest_plain.is_file():
        dest_plain.write_bytes(b"FRUTOOL_FULL_DEMO_FRU\n")
    return str(dest_plain)


def apply_full_demo(app_root: ApplicationRoot) -> None:
    """Fake connectivity, DHCP UI, FRU hints, topo match, and swap backup."""
    host = app_root.controller.host
    conn = app_root.conn
    network = conn.network

    bin_path = seed_demo_fru_backup()

    choice = NetworkChoice(
        alias="以太网 演示",
        description="Full Demo NIC",
        ipv4=DEMO_LOCAL_IP,
        prefix_length=24,
        status="Up",
        mac="00:11:22:33:44:55",
        ipv4_origin=IPV4_ORIGIN_MANUAL,
    )
    network.network_choices = [choice]
    network._selected_network_index = 0  # noqa: SLF001
    network.selectedNetworkIndexChanged.emit()
    host.network_model.setChoices([choice])

    network.apply_bmc_state_from_result({"bmc_online": True})
    network._local_online = True  # noqa: SLF001
    network.localOnlineChanged.emit()
    network.network_config = NetworkConfig(
        local_ip=DEMO_LOCAL_IP,
        bmc_ip=DEMO_BMC_IP,
        subnet_mask="255.255.255.0",
        prefix_length=24,
        interface_label=choice.alias,
    )
    network.bmcIpChanged.emit()
    network.localIpChanged.emit()
    network._network_summary = (  # noqa: SLF001
        f"演示模式 · 本机 {DEMO_LOCAL_IP} → BMC {DEMO_BMC_IP}（模拟 DHCP 已分配）"
    )
    network.networkSummaryChanged.emit()
    network._network_ip_warning = ""  # noqa: SLF001
    network.networkSummaryChanged.emit()

    # Credentials so write buttons stay enabled
    conn.setConnField("old_user", "admin")
    conn.setConnField("old_password", "admin")
    conn.setConnField("new_user", "admin")
    conn.setConnField("new_password", "admin")

    host.fru_field_model.setHints(DEMO_FRU_HINTS)
    # Prefill editable values so「刷写所有非空字段」可直接演示
    for i, (name, _area, _idx, _group) in enumerate(FRU_FIELDS):
        val = DEMO_FRU_HINTS.get(name, "")
        if val:
            host.fru_field_model.setValueAt(i, val)

    host.log("info", "—" * 24)
    host.log("info", "[演示] 全功能演示已启动（无真实硬件）")
    host.log("info", f"[演示] FRU 参考备份: {os.path.basename(bin_path)} · SN={DEMO_SN}")
    host.log("info", f"[演示] DHCP starting (local={DEMO_LOCAL_IP}, bmc={DEMO_BMC_IP})")
    host.log("info", f"[演示] DHCP Discover from MAC: {choice.mac}")
    host.log("info", f"[演示] DHCP Offer → {DEMO_BMC_IP}")
    host.log(
        "success",
        f"[演示] DHCP ACK to {choice.mac} ({DEMO_BMC_IP}) · 分配成功",
    )
    host.log(
        "info",
        "可演示：连接页 DHCP · 换板手动/自动（自动约十几秒走完离线→新板→克隆）· FRU · 拓扑（均为模拟）",
    )

    app_root.chrome.showPage("conn")

    # Trigger topo preload after hints settle
    from PyQt6.QtCore import QTimer

    def _open_and_match() -> None:
        app_root.ops._try_topo_match()  # noqa: SLF001

    QTimer.singleShot(600, _open_and_match)


def schedule_full_demo(app_root: ApplicationRoot) -> None:
    from PyQt6.QtCore import QTimer

    def _run() -> None:
        if not full_demo_enabled():
            return
        try:
            apply_full_demo(app_root)
        except Exception as exc:
            app_root.controller.host.log("critical", f"全功能演示初始化失败: {exc}")
            print(f"[FRUTool 全功能演示] 失败: {exc}", flush=True)

    QTimer.singleShot(400, _run)


def ensure_demo_env() -> None:
    """Set companion flags so existing swap/topo stubs also activate."""
    os.environ[DEMO_ALL_ENV] = "1"
    os.environ.setdefault("FRUTOOL_DEMO_SWAP", "1")
    os.environ.setdefault("FRUTOOL_DEMO_TOPO", "1")
    os.environ.setdefault("FRUTOOL_DEMO_SCENARIO", "multi")
    os.environ.setdefault("FRUTOOL_SKIP_ADMIN", "1")
