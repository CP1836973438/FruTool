"""DHCP protocol logic tests (no UDP 67 bind)."""
from __future__ import annotations

import socket
import time
from unittest.mock import patch

import pytest

from frutool.domain.dhcp import (
    DHCPServer,
    _diagnose_udp67_occupants,
    _log_dhcp_bind_failure,
    _lookup_process_name,
)
from frutool.infrastructure.network import NetworkConfig
from tests.dhcp_helpers import (
    decline_packet,
    discover_packet,
    request_packet_requested_ip,
    request_packet_server_id,
)


@pytest.fixture
def sample_net() -> NetworkConfig:
    return NetworkConfig(
        local_ip="192.168.1.100",
        bmc_ip="192.168.1.200",
        subnet_mask="255.255.255.0",
        prefix_length=24,
        interface_label="Test NIC",
    )


@pytest.fixture
def dhcp_server(log_collector, sample_net):
    entries, log = log_collector
    srv = DHCPServer(log, lambda: sample_net)
    return srv, entries, log, sample_net


class TestDhcpOptionParsing:
    def test_parse_options_roundtrip(self):
        raw = bytes([53, 1, 3, 54, 4, 192, 168, 1, 1, 255])
        parsed = DHCPServer._parse_options(raw)
        assert parsed[53] == b"\x03"
        assert parsed[54] == socket.inet_aton("192.168.1.1")

    def test_option_byte_returns_single_byte(self):
        assert DHCPServer._option_byte({53: b"\x01"}, 53) == 1
        assert DHCPServer._option_byte({53: b"\x01\x02"}, 53) is None
        assert DHCPServer._option_byte({}, 53) is None

    def test_put_option_advances_position(self):
        reply = bytearray(64)
        pos = DHCPServer._put_option(reply, 0, 53, b"\x02")
        assert pos == 3
        assert reply[0:3] == bytes([53, 1, 2])


class TestDhcpBuildReply:
    def test_offer_includes_lease_options(self, dhcp_server, sample_net):
        srv, *_ = dhcp_server
        discover = discover_packet()
        reply = srv._build_reply(discover, sample_net, sample_net.bmc_ip, 2)
        assert reply[0] == 2
        assert reply[16:20] == socket.inet_aton(sample_net.bmc_ip)
        assert reply[20:24] == socket.inet_aton(sample_net.local_ip)
        assert DHCPServer.MAGIC in reply

    def test_nak_omits_lease_options(self, dhcp_server, sample_net):
        srv, *_ = dhcp_server
        discover = discover_packet()
        reply = srv._build_reply(discover, sample_net, "0.0.0.0", 6)
        assert 51 not in reply[240:]


class TestDhcpDiscover:
    def test_discover_creates_pending_lease(self, dhcp_server):
        srv, entries, _, sample_net = dhcp_server
        xid = 0xAABBCCDD
        with patch.object(srv, "_send_dhcp_reply", return_value="192.168.1.255") as send_mock:
            srv._handle_dhcp_packet(discover_packet(xid=xid))
        assert xid in srv.pending_leases
        assert srv.pending_leases[xid]["bmc_ip"] == sample_net.bmc_ip
        assert send_mock.called
        assert any("Discover" in msg for _, msg in entries)
        assert any(sample_net.bmc_ip in msg and "OFFER" in msg for _, msg in entries)

    def test_discover_send_failure_logs_warning(self, dhcp_server):
        srv, entries, _, _ = dhcp_server
        with patch.object(srv, "_send_dhcp_reply", return_value=None):
            srv._handle_dhcp_packet(discover_packet())
        assert any(level == "warning" and "OFFER send failed" in msg for level, msg in entries)


class TestDhcpRequestAck:
    def test_request_with_server_id_triggers_ack(self, dhcp_server):
        srv, entries, _, sample_net = dhcp_server
        xid = 0x01020304
        acks: list[tuple[str, str]] = []
        srv.on_ack_sent = lambda mac, ip: acks.append((mac, ip))
        srv.pending_leases[xid] = {"mac": "AA:BB:CC:DD:EE:FF", "bmc_ip": sample_net.bmc_ip, "expire": time.time() + 30}
        with patch.object(srv, "_send_dhcp_reply", return_value="192.168.1.255"):
            srv._handle_dhcp_packet(
                request_packet_server_id(xid=xid, mac=b"\xaa\xbb\xcc\xdd\xee\xff", server_ip=sample_net.local_ip)
            )
        assert xid not in srv.pending_leases
        assert "AA:BB:CC:DD:EE:FF" in srv.active_leases
        assert acks == [("AA:BB:CC:DD:EE:FF", sample_net.bmc_ip)]
        assert any(level == "success" and "Assigned" in msg for level, msg in entries)

    def test_init_reboot_matching_ip_acks(self, dhcp_server, sample_net):
        srv, entries, _, _ = dhcp_server
        acks: list[tuple[str, str]] = []
        srv.on_ack_sent = lambda mac, ip: acks.append((mac, ip))
        with patch.object(srv, "_send_dhcp_reply", return_value="192.168.1.255"):
            srv._handle_dhcp_packet(
                request_packet_requested_ip(requested_ip=sample_net.bmc_ip)
            )
        assert acks == [("AA:BB:CC:DD:EE:FF", sample_net.bmc_ip)]
        assert any("INIT-REBOOT" in msg and "ACK" in msg for _, msg in entries)

    def test_init_reboot_mismatch_sends_nak(self, dhcp_server, sample_net):
        srv, entries, _, _ = dhcp_server
        with patch.object(srv, "_send_dhcp_reply", return_value="192.168.1.255") as send_mock:
            srv._handle_dhcp_packet(request_packet_requested_ip(requested_ip="192.168.1.50"))
        send_mock.assert_called_once()
        payload = send_mock.call_args[0][0]
        assert payload[0] == 2
        assert any("NAK sent" in msg for _, msg in entries)

    def test_request_without_pending_lease_logs_warning(self, dhcp_server, sample_net):
        srv, entries, _, _ = dhcp_server
        xid = 0x0A0B0C0D
        srv._handle_dhcp_packet(
            request_packet_server_id(xid=xid, mac=b"\xaa\xbb\xcc\xdd\xee\xff", server_ip=sample_net.local_ip)
        )
        assert any(level == "warning" and "no pending lease" in msg for level, msg in entries)

    def test_request_without_options_still_acks(self, dhcp_server):
        srv, _, _, sample_net = dhcp_server
        from tests.dhcp_helpers import build_dhcp_packet

        acks: list[tuple[str, str]] = []
        srv.on_ack_sent = lambda mac, ip: acks.append((mac, ip))
        bare_request = build_dhcp_packet(options=[(53, b"\x03")])
        with patch.object(srv, "_send_dhcp_reply", return_value="192.168.1.255"):
            srv._handle_dhcp_packet(bare_request)
        assert acks == [("AA:BB:CC:DD:EE:FF", sample_net.bmc_ip)]


class TestDhcpDecline:
    def test_decline_releases_active_lease(self, dhcp_server):
        srv, entries, _, sample_net = dhcp_server
        mac = "AA:BB:CC:DD:EE:FF"
        srv.active_leases[mac] = {"ip": sample_net.bmc_ip, "expire": time.time() + 100}
        srv._handle_dhcp_packet(decline_packet())
        assert mac not in srv.active_leases
        assert any("Decline" in msg for _, msg in entries)


class TestDhcpBindFailureDiagnostics:
    def test_permission_error_message(self, log_collector):
        entries, log = log_collector
        _log_dhcp_bind_failure(log, PermissionError())
        assert any("administrator" in msg.lower() for _, msg in entries)

    def test_port_in_use_lists_occupants(self, log_collector, monkeypatch):
        entries, log = log_collector
        monkeypatch.setattr(
            "frutool.domain.dhcp._diagnose_udp67_occupants",
            lambda: [("0.0.0.0", "1234", "vmnetdhcp.exe")],
        )
        _log_dhcp_bind_failure(log, OSError(10048, "address already in use"))
        assert any("vmnetdhcp.exe" in msg for _, msg in entries)
        assert any("possible causes" in msg.lower() or "DHCP bind failure" in msg for _, msg in entries)

    def test_diagnose_parses_netstat_output(self, monkeypatch):
        netstat_out = "  UDP    0.0.0.0:67           *:*                                    4321\n"
        monkeypatch.setattr(
            "frutool.domain.dhcp.subprocess.run",
            lambda *a, **k: type("R", (), {"returncode": 0, "stdout": netstat_out})(),
        )
        monkeypatch.setattr("frutool.domain.dhcp._lookup_process_name", lambda pid: "testdhcp.exe")
        occupants = _diagnose_udp67_occupants()
        assert occupants == [("0.0.0.0", "4321", "testdhcp.exe")]

    def test_lookup_process_name_non_windows(self, monkeypatch):
        monkeypatch.setattr("frutool.domain.dhcp.sys.platform", "linux")
        assert _lookup_process_name("1234") == ""


class TestDhcpBindAddress:
    def test_run_binds_any_address_to_receive_limited_broadcast(self, log_collector, sample_net):
        entries, log = log_collector
        srv = DHCPServer(log, lambda: sample_net)
        binds: list[tuple] = []

        class FakeSock:
            def setsockopt(self, *a, **k):
                return None

            def settimeout(self, *_a, **_k):
                return None

            def bind(self, addr):
                binds.append(addr)
                raise OSError("stop after bind")

            def close(self):
                return None

        with patch("frutool.domain.dhcp.socket.socket", return_value=FakeSock()):
            srv.run()
        assert binds == [("", 67)]
        assert any("Cannot bind" in msg or "DHCP" in msg for _, msg in entries)

    def test_reply_stays_bound_to_selected_nic(self, dhcp_server):
        srv, _, _, _ = dhcp_server
        binds: list[tuple] = []
        destinations: list[tuple] = []

        class FakeSock:
            def setsockopt(self, *_a):
                return None

            def bind(self, addr):
                binds.append(addr)

            def sendto(self, _payload, destination):
                destinations.append(destination)

            def close(self):
                return None

        with patch("frutool.domain.dhcp.socket.socket", return_value=FakeSock()):
            result = srv._send_dhcp_reply(
                b"reply", "192.168.1.100", "192.168.1.255"
            )
        assert binds == [("192.168.1.100", 0)]
        assert ("192.168.1.255", 68) in destinations
        assert result == "192.168.1.255"
