"""Tests for log tab classification."""
from __future__ import annotations

from frutool.infrastructure.log_util import classify_log
from frutool.theme.tokens import log_prefix


class TestLogLevelPrefix:
    def test_success_uses_success_label(self):
        assert log_prefix("success") == "SUCCESS"


class TestDhcpLogClassification:
    def test_bind_failure_hints_and_advice(self):
        assert "dhcp" in classify_log("DHCP bind failure — possible causes:")
        assert "dhcp" in classify_log("  - Windows ICS（Internet 连接共享）")
        assert "dhcp" in classify_log(
            "DHCP: close the conflicting service or process, then refresh the network adapter or restart this tool."
        )

    def test_lifecycle_messages(self):
        assert "dhcp" in classify_log("DHCP starting (local=192.168.1.100, bmc=192.168.1.200)")
        assert "dhcp" in classify_log("DHCP probe grace 3s after ACK to AA:BB:CC:DD:EE:FF (192.168.1.200)")

    def test_no_pending_lease_warning(self):
        assert "dhcp" in classify_log(
            "DHCP Request from AA:BB:CC:DD:EE:FF: no pending lease for xid=0x01020304 (option 54), ignored"
        )

    def test_network_config_summary(self):
        assert "dhcp" in classify_log("网卡配置：来源：网卡；本机 IPv4：192.168.1.100/24")
