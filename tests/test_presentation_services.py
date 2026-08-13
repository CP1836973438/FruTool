"""Tests for presentation service layer (no full QML)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from frutool.domain.ipmi import FruFingerprint
from frutool.infrastructure.network import IPV4_ORIGIN_DHCP, IPV4_ORIGIN_MANUAL, NetworkChoice, NetworkConfig
from frutool.presentation.controller.network_controller import NetworkController
from frutool.presentation.services.network_runtime_service import (
    config_after_choice,
    describe_link_transition,
    network_choices_usable,
    normalize_network_choices,
    restart_dhcp_server,
    run_enumerate_networks_job,
    should_run_dhcp,
)
from frutool.presentation.services.swap_auto_service import SwapAutoService
from frutool.presentation.services.swap_service import SwapSessionService


class TestSwapAutoService:
    def test_phase_running_delegates_to_domain(self):
        svc = SwapAutoService(SwapSessionService("/tmp/unused.json"))
        svc.state.phase = "wait_swap"
        assert svc.phase_running() is True

    def test_status_text_empty_in_manual_mode(self):
        svc = SwapAutoService(SwapSessionService("/tmp/unused.json"))
        svc.state.mode = "manual"
        assert svc.status_text(wait_new_text="x") == ""

    def test_status_text_in_auto_mode(self):
        svc = SwapAutoService(SwapSessionService("/tmp/unused.json"))
        svc.state.mode = "auto"
        svc.state.phase = "wait_swap"
        text = svc.status_text(wait_new_text="")
        assert "等待" in text or "换板" in text

    def test_persist_skips_when_not_resumable(self, tmp_path):
        path = str(tmp_path / "session.json")
        svc = SwapAutoService(SwapSessionService(path))
        svc.state.mode = "auto"
        svc.state.phase = "idle"
        assert svc.persist(closing=False, sn="SN1", step1_done=False, step2_done=False, new_board_fru_backup_path=None) is None
        assert not (tmp_path / "session.json").exists()

    def test_persist_writes_session_file(self, tmp_path):
        path = str(tmp_path / "session.json")
        svc = SwapAutoService(SwapSessionService(path))
        svc.state.mode = "auto"
        svc.state.phase = "wait_swap"
        svc.state.old_fingerprint = FruFingerprint("B1", "P1", "Board")
        err = svc.persist(
            closing=False,
            sn="SN1",
            step1_done=True,
            step2_done=False,
            new_board_fru_backup_path=None,
        )
        assert err is None
        assert (tmp_path / "session.json").is_file()

    def test_reset_runtime_clears_poll_state(self):
        svc = SwapAutoService(SwapSessionService("/tmp/unused.json"))
        svc.state.poll_in_flight = True
        svc.state.poll_started_at = 1.0
        svc.state.offline_streak = 5
        svc.reset_runtime()
        assert svc.state.poll_in_flight is False
        assert svc.state.offline_streak == 0

    def test_set_phase_refresh_on_wait_swap(self):
        svc = SwapAutoService(SwapSessionService("/tmp/unused.json"))
        assert svc.set_phase("wait_swap") is True
        assert svc.set_phase("idle") is True


class TestNetworkRuntimeService:
    def test_normalize_invalid_choices(self):
        choices, index = normalize_network_choices("bad", "192.168.1.2", lambda c: 0)
        assert choices == []
        assert index == 0

    def test_normalize_prefers_previous_ip(self):
        items = [
            NetworkChoice("eth0", "NIC", "192.168.1.10", 24),
            NetworkChoice("eth1", "NIC", "192.168.1.20", 24),
        ]
        choices, index = normalize_network_choices(items, "192.168.1.20", lambda c: 0)
        assert index == 1

    def test_describe_link_transition_connect(self):
        msg, offline = describe_link_transition(False, True, "以太网")
        assert msg == ("info", "网卡链路已连接：以太网，刷新网卡并同步 DHCP…")
        assert offline is False

    def test_describe_link_transition_initial_up(self):
        msg, offline = describe_link_transition(None, True, "以太网")
        assert msg is not None
        assert "同步 DHCP" in msg[1]
        assert offline is False

    def test_describe_link_transition_initial_down(self):
        assert describe_link_transition(None, False, "以太网") == (None, True)

    def test_describe_link_transition_disconnect(self):
        msg, offline = describe_link_transition(True, False, "以太网")
        assert msg is not None
        assert "已断开" in msg[1]
        assert "停止内置 DHCP" not in msg[1]
        assert offline is True

    def test_describe_link_transition_unchanged(self):
        assert describe_link_transition(True, True, "eth0") == (None, False)

    def test_network_choices_usable(self):
        assert network_choices_usable([]) is False
        assert network_choices_usable([NetworkChoice("eth0", "NIC", "", 24)]) is False
        assert network_choices_usable([NetworkChoice("eth0", "NIC", "192.168.1.2", 24)]) is True

    def test_enumerate_job_timeout(self, log_collector, monkeypatch):
        import time

        entries, log = log_collector
        monkeypatch.setattr(
            "frutool.presentation.services.network_runtime_service.NETWORK_ENUM_JOB_TIMEOUT_S",
            0.05,
        )

        def slow_enum():
            time.sleep(0.2)
            return []

        monkeypatch.setattr(
            "frutool.presentation.services.network_runtime_service.enumerate_ipv4_interfaces",
            slow_enum,
        )
        with pytest.raises(TimeoutError, match="network enumeration exceeded"):
            run_enumerate_networks_job(log)
        assert any("网卡枚举超时" in e[1] for e in entries)

    def test_config_after_choice(self):
        choice = NetworkChoice(
            "eth0", "USB NIC", "192.168.1.100", 24, ipv4_origin=IPV4_ORIGIN_MANUAL
        )
        config, summary = config_after_choice(choice)
        assert isinstance(config, NetworkConfig)
        assert config.local_ip == "192.168.1.100"
        assert "192.168.1.100" in summary

    def test_config_after_unusable_choice_clears_addresses(self):
        choice = NetworkChoice("eth0", "USB NIC", "169.254.1.5", 16)
        config, summary = config_after_choice(choice)
        assert config.local_ip == ""
        assert "—" in summary or "无可用" in summary

    def test_should_run_dhcp_manual_link_up(self):
        choice = NetworkChoice(
            "eth0", "NIC", "192.168.1.2", 24, ipv4_origin=IPV4_ORIGIN_MANUAL
        )
        run, reason = should_run_dhcp(choice, True)
        assert run is True
        assert reason == ""

    def test_should_run_dhcp_pauses_windows_dhcp_client(self):
        choice = NetworkChoice(
            "eth0", "NIC", "10.0.0.5", 24, ipv4_origin=IPV4_ORIGIN_DHCP
        )
        run, reason = should_run_dhcp(choice, True)
        assert run is False
        assert "DHCP 客户端" in reason

    def test_should_run_dhcp_pauses_on_link_down(self):
        choice = NetworkChoice(
            "eth0", "NIC", "192.168.1.2", 24, ipv4_origin=IPV4_ORIGIN_MANUAL
        )
        # Link down must NOT pause DHCP — auto-swap unplugs between boards.
        run, reason = should_run_dhcp(choice, False)
        assert run is True
        assert reason == ""

    def test_should_run_dhcp_pauses_unknown_origin(self):
        choice = NetworkChoice("eth0", "NIC", "192.168.1.2", 24)
        run, reason = should_run_dhcp(choice, True)
        assert run is True
        assert reason == ""

    def test_should_run_dhcp_allows_when_link_unknown(self):
        choice = NetworkChoice(
            "eth0", "NIC", "192.168.1.2", 24, ipv4_origin=IPV4_ORIGIN_MANUAL
        )
        run, reason = should_run_dhcp(choice, None)
        assert run is True
        assert reason == ""

    def test_restart_dhcp_stops_old_server(self, log_collector):
        entries, log = log_collector
        old = MagicMock()
        config = NetworkConfig("192.168.1.100", "192.168.1.200", "255.255.255.0", 24, "eth0")
        with patch("frutool.presentation.services.network_runtime_service.DHCPServer") as mock_cls:
            new_server = MagicMock()
            mock_cls.return_value = new_server
            result = restart_dhcp_server(old, log, lambda: config)
        old.stop.assert_called_once()
        old.join.assert_called_once()
        new_server.start.assert_called_once()
        assert result is new_server
        assert any("DHCP stopping" in msg for _, msg in entries)
        assert any("DHCP server stopped" in msg for _, msg in entries)
        assert any("DHCP starting" in msg for _, msg in entries)

    def test_restart_dhcp_pauses_without_starting(self, log_collector):
        entries, log = log_collector
        old = MagicMock()
        config = NetworkConfig("192.168.1.100", "192.168.1.200", "255.255.255.0", 24, "eth0")
        with patch("frutool.presentation.services.network_runtime_service.DHCPServer") as mock_cls:
            result = restart_dhcp_server(
                old,
                log,
                lambda: config,
                should_run=False,
                pause_reason="office dhcp",
            )
        old.stop.assert_called_once()
        mock_cls.assert_not_called()
        assert result is None
        assert any("DHCP paused" in msg for _, msg in entries)

    def test_sync_keeps_healthy_dhcp_when_gate_state_is_unchanged(self):
        choice = NetworkChoice(
            "eth0", "NIC", "192.168.1.2", 24, ipv4_origin=IPV4_ORIGIN_MANUAL
        )
        controller = MagicMock()
        controller._current_network_choice.return_value = choice
        controller._link_up = True
        controller.network_config = NetworkConfig(
            "192.168.1.2", "192.168.1.100", "255.255.255.0", 24, "eth0"
        )
        controller._dhcp_server.is_alive.return_value = True
        controller._dhcp_sync_key = (
            True, "192.168.1.2", "192.168.1.100", 24, "eth0", ""
        )
        with patch(
            "frutool.presentation.controller.network_controller.restart_dhcp_server"
        ) as restart:
            NetworkController._sync_dhcp(controller)
        restart.assert_not_called()
