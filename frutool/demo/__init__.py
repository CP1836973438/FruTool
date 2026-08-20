"""Development demos (also available in packaged builds via env flags)."""

from __future__ import annotations

import os

DEMO_TOPO_ENV = "FRUTOOL_DEMO_TOPO"
DEMO_SWAP_ENV = "FRUTOOL_DEMO_SWAP"
DEMO_SKIP_SN = "12345678"


def topo_demo_enabled() -> bool:
    return os.environ.get(DEMO_TOPO_ENV) == "1"


def swap_demo_enabled() -> bool:
    return os.environ.get(DEMO_SWAP_ENV) == "1"


def fake_bmc_enabled() -> bool:
    """Skip real NIC/BMC probe and keep status lights on."""
    return topo_demo_enabled() or swap_demo_enabled()
