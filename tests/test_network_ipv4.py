"""Tests for IPv4 usability checks used by BMC DHCP."""
from __future__ import annotations

import pytest

from frutool.infrastructure.network import (
    IPV4_ORIGIN_DHCP,
    IPV4_ORIGIN_MANUAL,
    NetworkChoice,
    explain_unusable_host_ipv4,
    is_dhcp_usable_host_ipv4,
    make_network_config,
    normalize_ipv4_origin,
)
from frutool.presentation.services.network_service import format_network_ip_warning, format_network_summary


class TestExplainUnusableHostIpv4:
    @pytest.mark.parametrize(
        "ip,expected_fragment",
        [
            ("0.0.0.0", "未指定"),
            ("0.0.0.7", "未指定"),
            ("127.0.0.1", "环回"),
            ("255.255.255.255", "广播"),
            ("169.254.12.34", "APIPA"),
            ("224.0.0.1", "组播"),
            ("240.0.0.1", "保留"),
            ("192.168.1.0", "网络地址"),
            ("192.168.1.255", "广播地址"),
        ],
    )
    def test_unusable_addresses(self, ip, expected_fragment):
        reason = explain_unusable_host_ipv4(ip, 24)
        assert reason is not None
        assert expected_fragment in reason

    @pytest.mark.parametrize(
        "ip",
        [
            "192.168.1.2",
            "10.10.10.50",
            "172.16.0.10",
        ],
    )
    def test_usable_addresses(self, ip):
        assert explain_unusable_host_ipv4(ip, 24) is None
        assert is_dhcp_usable_host_ipv4(ip, 24) is True

    def test_invalid_format(self):
        assert explain_unusable_host_ipv4("not-an-ip") is not None


class TestNetworkChoiceLabel:
    def test_label_marks_unusable_ip(self):
        choice = NetworkChoice("以太网", "Realtek", "169.254.1.10", 16, "Up")
        assert "[不可用]" in choice.label
        assert "169.254.1.10" in choice.label

    def test_label_marks_dhcp_origin(self):
        choice = NetworkChoice(
            "以太网", "Realtek", "10.0.0.8", 24, "Up", ipv4_origin=IPV4_ORIGIN_DHCP
        )
        assert "[DHCP]" in choice.label

    def test_label_marks_manual_origin(self):
        choice = NetworkChoice(
            "以太网", "Realtek", "192.168.1.2", 24, "Up", ipv4_origin=IPV4_ORIGIN_MANUAL
        )
        assert "[静态]" in choice.label


class TestNormalizeIpv4Origin:
    def test_manual_and_dhcp(self):
        assert normalize_ipv4_origin("Manual") == IPV4_ORIGIN_MANUAL
        assert normalize_ipv4_origin("Dhcp") == IPV4_ORIGIN_DHCP
        assert normalize_ipv4_origin("yes") == IPV4_ORIGIN_DHCP
        assert normalize_ipv4_origin("") == "Unknown"

    def test_powershell_json_int_enums(self):
        assert normalize_ipv4_origin(1) == IPV4_ORIGIN_MANUAL
        assert normalize_ipv4_origin(3) == IPV4_ORIGIN_DHCP
        assert normalize_ipv4_origin("1") == IPV4_ORIGIN_MANUAL
        assert normalize_ipv4_origin("3") == IPV4_ORIGIN_DHCP

    def test_dhcp_disabled_is_manual(self):
        assert normalize_ipv4_origin("Disabled") == IPV4_ORIGIN_MANUAL


class TestMakeNetworkConfig:
    def test_unusable_ip_clears_addresses(self):
        choice = NetworkChoice("以太网", "Realtek", "169.254.1.10", 16, "Up")
        config = make_network_config(choice)
        assert config.local_ip == ""
        assert config.bmc_ip == ""
        assert config.interface_label == "Unavailable"

    def test_disconnected_nic_clears_addresses(self):
        choice = NetworkChoice("以太网", "Killer", "", 24, "Disconnected")
        config = make_network_config(choice)
        assert config.local_ip == ""
        assert config.bmc_ip == ""


class TestNetworkSummaryWarning:
    def test_warning_for_apipa(self):
        choice = NetworkChoice("以太网", "Realtek", "169.254.88.1", 16, "Up")
        warning = format_network_ip_warning(choice)
        assert "169.254.88.1" in warning
        assert "静态 IPv4" in warning

    def test_warning_for_windows_dhcp_client(self):
        choice = NetworkChoice(
            "以太网", "Realtek", "10.1.2.3", 24, "Up", ipv4_origin=IPV4_ORIGIN_DHCP
        )
        warning = format_network_ip_warning(choice)
        assert "DHCP 客户端" in warning
        assert "已暂停" in warning

    def test_summary_includes_warning(self):
        choice = NetworkChoice("以太网", "Realtek", "169.254.88.1", 16, "Up")
        config = make_network_config(choice)
        summary = format_network_summary(config, choice)
        assert "169.254.88.1" in summary
        assert "无法为 BMC 提供 DHCP" in summary

    def test_warning_for_disconnected_nic(self):
        choice = NetworkChoice("以太网", "Killer", "", 24, "Disconnected")
        warning = format_network_ip_warning(choice)
        assert "未连接" in warning or "无 IPv4" in warning

    def test_summary_disconnected_has_no_fake_ip(self):
        choice = NetworkChoice("以太网", "Killer", "", 24, "Disconnected")
        config = make_network_config(choice)
        summary = format_network_summary(config, choice)
        assert config.local_ip == ""
        assert "本机 IPv4：—" in summary
        assert "本机 IPv4：192.168.1.2" not in summary
