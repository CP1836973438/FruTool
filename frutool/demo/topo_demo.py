"""Topology UI demo — fake BMC + FRU hints, no real hardware required."""

from __future__ import annotations



import os

from dataclasses import dataclass

from typing import TYPE_CHECKING, Optional



from frutool.infrastructure.network import NetworkConfig



if TYPE_CHECKING:

    from frutool.presentation.app import ApplicationRoot



DEMO_ENV = "FRUTOOL_DEMO_TOPO"

SCENARIO_ENV = "FRUTOOL_DEMO_SCENARIO"





@dataclass(frozen=True)

class TopoDemoScenario:

    key: str

    title: str

    description: str

    product_extra: str

    product_manufacturer: str

    bmc_ip: str = "192.168.70.100"





SCENARIOS: dict[str, TopoDemoScenario] = {

    "multi": TopoDemoScenario(

        key="multi",

        title="同套餐多厂商",

        description="M51M1-I9DD2M + Inspur；PCLE 压缩包文件名需含厂商名（如 Inspur-YICHUN-topo.zip）。",

        product_extra="Suite:M51M1-I9DD2M",

        product_manufacturer="Inspur",

    ),

    "foxconn": TopoDemoScenario(

        key="foxconn",

        title="推荐 FOXCONN",

        description="同一套餐，Product Manufacturer 设为 FOXCONN。",

        product_extra="Suite:M51M1-I9DD2M",

        product_manufacturer="FOXCONN",

    ),

    "single": TopoDemoScenario(

        key="single",

        title="单条匹配",

        description="较少冲突的套餐号，通常只预加载一条。",

        product_extra="Suite:M76M1-I9DD2M-EU",

        product_manufacturer="Inventec",

    ),

    "missing": TopoDemoScenario(

        key="missing",

        title="未找到套餐",

        description="PCLE 中不存在的套餐号，仅展示拓扑库与提示信息。",

        product_extra="Suite:NOT-EXIST-DEMO-999",

        product_manufacturer="Inspur",

    ),

}





def demo_enabled() -> bool:

    return os.environ.get(DEMO_ENV) == "1"





def resolve_scenario(name: Optional[str] = None) -> TopoDemoScenario:

    key = (name or os.environ.get(SCENARIO_ENV) or "multi").strip().lower()

    if key not in SCENARIOS:

        known = ", ".join(sorted(SCENARIOS))

        raise ValueError(f"未知演示场景 '{key}'，可选: {known}")

    return SCENARIOS[key]





def list_scenarios() -> list[TopoDemoScenario]:

    return list(SCENARIOS.values())





def _demo_fru_hints(scenario: TopoDemoScenario) -> dict[str, str]:

    return {

        "Chassis Part Number": "",

        "Chassis Serial": "",

        "Board Mfg": "DemoBoard",

        "Board Product": "Demo SKU",

        "Board Serial": "DEMO-BOARD-001",

        "Board Part Number": "",

        "Product Manufacturer": scenario.product_manufacturer,

        "Product Name": "Demo New Board",

        "Product Part Number": "DEMO-PN",

        "Product Version": "A1",

        "Product Serial": "DEMO-SN-2026",

        "Product Asset Tag": "",

        "Product Extra": scenario.product_extra,

    }





def apply_topo_demo(app_root: ApplicationRoot, scenario_name: Optional[str] = None) -> TopoDemoScenario:

    """Apply fake connectivity + FRU hints and open the topology page."""

    scenario = resolve_scenario(scenario_name)

    host = app_root.controller.host

    conn = app_root.conn

    network = conn.network



    network.apply_bmc_state_from_result({"bmc_online": True})

    network._local_online = True  # noqa: SLF001 — demo-only fake link state

    network.localOnlineChanged.emit()

    cfg = network.network_config

    network.network_config = NetworkConfig(

        local_ip=cfg.local_ip or "192.168.70.2",

        bmc_ip=scenario.bmc_ip,

        subnet_mask=cfg.subnet_mask,

        prefix_length=cfg.prefix_length,

        interface_label="Demo",

    )

    network.bmcIpChanged.emit()

    network._network_summary = f"演示模式 · BMC {scenario.bmc_ip}（模拟在线）"

    network.networkSummaryChanged.emit()



    host.fru_field_model.setHints(_demo_fru_hints(scenario))

    app_root.chrome.showPage("topo")



    host.log(

        "info",

        f"拓扑演示 [{scenario.key}] {scenario.title} — {scenario.description}",

    )

    return scenario





def schedule_topo_demo(app_root: ApplicationRoot) -> None:

    """Run demo setup shortly after QML is shown."""

    from PyQt6.QtCore import QTimer



    def _run() -> None:

        try:

            scenario = apply_topo_demo(app_root)

            print(

                f"[FRUTool 拓扑演示] 场景={scenario.key} · {scenario.title}\n"

                f"  Product Extra: {scenario.product_extra}\n"

                f"  Product Manufacturer: {scenario.product_manufacturer}\n"

                f"  切换场景: $env:FRUTOOL_DEMO_SCENARIO='foxconn' 后重新运行脚本",

                flush=True,

            )

        except Exception as exc:

            app_root.controller.host.log("critical", f"拓扑演示初始化失败: {exc}")

            print(f"[FRUTool 拓扑演示] 失败: {exc}", flush=True)



    QTimer.singleShot(350, _run)

