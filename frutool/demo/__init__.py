"""Development demos (also available in packaged builds via env flags)."""

from __future__ import annotations

import os

DEMO_TOPO_ENV = "FRUTOOL_DEMO_TOPO"
DEMO_SWAP_ENV = "FRUTOOL_DEMO_SWAP"
DEMO_ALL_ENV = "FRUTOOL_DEMO_ALL"
# Sample board Product Serial / backup stem (fru_backup/21D111761_*.bin)
DEMO_SN = "21D111761"
DEMO_SKIP_SN = DEMO_SN


def topo_demo_enabled() -> bool:
    return os.environ.get(DEMO_TOPO_ENV) == "1" or full_demo_enabled()


def swap_demo_enabled() -> bool:
    return os.environ.get(DEMO_SWAP_ENV) == "1" or full_demo_enabled()


def full_demo_enabled() -> bool:
    return os.environ.get(DEMO_ALL_ENV) == "1"


def fake_bmc_enabled() -> bool:
    """Skip real NIC/BMC probe and keep status lights on."""
    return topo_demo_enabled() or swap_demo_enabled() or full_demo_enabled()


def hardware_sim_enabled() -> bool:
    """Fake successful FRU / topology / swap writes (no real IPMI)."""
    return full_demo_enabled() or swap_demo_enabled() or topo_demo_enabled()
