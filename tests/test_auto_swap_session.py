"""AutoSwapSessionController tests with mocked host/workflow."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from frutool.domain.ipmi import FruFingerprint
from frutool.domain.swap.session import build_session_payload, save_session
from frutool.presentation.controller.auto_swap_session import AutoSwapSessionController
from frutool.presentation.controller.swap_progress import SwapProgress
from frutool.presentation.services import SwapAutoService, SwapSessionService


class FakeWorkflow:
    def __init__(self) -> None:
        self.export_started = False
        self.sn_confirm_fp: FruFingerprint | None = None
        self.poll_started = False
        self.sn_detect_started = False

    def start_export(self) -> None:
        self.export_started = True

    def show_sn_confirm(self, fp: FruFingerprint) -> None:
        self.sn_confirm_fp = fp

    def start_sn_detect(self) -> None:
        self.sn_detect_started = True

    def on_poll_tick(self) -> None:
        pass


@pytest.fixture
def swap_session_stack(qapp, fake_host, tmp_path):
    session_path = str(tmp_path / "swap_session.json")
    fake_host.swap_auto = SwapAutoService(SwapSessionService(session_path))
    progress = SwapProgress(fake_host, fake_host.swap_auto)
    conn = SimpleNamespace(bmcOnline=True)
    controller = AutoSwapSessionController(fake_host, conn, progress)
    workflow = FakeWorkflow()
    controller.bind_workflow(workflow)
    return controller, fake_host, progress, workflow, session_path


class TestSnConfirmResponse:
    def test_accepted_starts_export(self, swap_session_stack):
        controller, host, _, workflow, _ = swap_session_stack
        fp = FruFingerprint("B1", "P1", "Board")
        controller._swap_auto.state.pending_sn_confirm_fp = fp
        controller.sn_confirm_response("dlg-1", True)
        assert workflow.export_started is True
        assert controller._swap_auto.state.pending_sn_confirm_fp is None
        assert any("[Auto] SN 已确认" in msg for _, msg in host.logs)

    def test_rejected_resets_to_manual(self, swap_session_stack):
        controller, host, _, workflow, _ = swap_session_stack
        fp = FruFingerprint("B1", "P1", "Board")
        controller._swap_auto.state.mode = "auto"
        controller._swap_auto.state.phase = "sn_confirm"
        controller._swap_auto.state.pending_sn_confirm_fp = fp
        controller.sn_confirm_response("dlg-2", False)
        assert workflow.export_started is False
        assert controller._swap_auto.state.mode == "manual"
        assert controller._swap_auto.state.phase == "idle"
        assert any("已取消" in msg for _, msg in host.logs)


class TestRestoreSession:
    def test_restore_wait_swap_after_accept(self, swap_session_stack, tmp_path):
        controller, host, progress, workflow, session_path = swap_session_stack
        bin_path = tmp_path / "SN001_20260101.bin"
        bin_path.write_text("")
        save_session(
            session_path,
            build_session_payload(
                auto_phase="wait_swap",
                sn="SN001",
                step1_done=True,
                step2_done=False,
                old_fingerprint={"board_serial": "B1", "product_serial": "P1", "product_name": "X"},
                wait_new_started_at=None,
                last_export_bin=bin_path.name,
                new_board_fru_backup_path=None,
            ),
        )
        controller.restore_session()
        assert len(host.questions) == 1
        _, _, on_restore = host.questions[0]
        on_restore(True)
        assert controller.swapAutoPhase == "wait_swap"
        assert controller.swapMode == "auto"
        assert progress.old_board_sn == "SN001"
        assert controller._poll_timer.isActive()

    def test_restore_sn_confirm_shows_dialog(self, swap_session_stack):
        controller, host, _, workflow, session_path = swap_session_stack
        fp = {"board_serial": "B1", "product_serial": "P1", "product_name": "Board"}
        save_session(
            session_path,
            build_session_payload(
                auto_phase="sn_confirm",
                sn="SN002",
                step1_done=False,
                step2_done=False,
                old_fingerprint=fp,
                wait_new_started_at=None,
                last_export_bin=None,
                new_board_fru_backup_path=None,
            ),
        )
        controller.restore_session()
        on_restore = host.questions[0][2]
        on_restore(True)
        assert workflow.sn_confirm_fp is not None
        assert workflow.sn_confirm_fp.board_serial == "B1"

    def test_restore_timeout_clears_session(self, swap_session_stack):
        controller, host, _, _, session_path = swap_session_stack
        save_session(
            session_path,
            {
                "version": 1,
                "swap_mode": "auto",
                "swap_auto_phase": "wait_new",
                "sn": "SN003",
                "step1_done": True,
                "step2_done": False,
                "old_fingerprint": None,
                "wait_new_started_at": "2020-01-01T00:00:00",
                "last_export_bin": None,
                "new_board_fru_backup_path": None,
            },
        )
        controller.restore_session()
        assert len(host.warnings) == 1
        assert not Path(session_path).exists()

    def test_restore_declined_clears_session(self, swap_session_stack):
        controller, host, _, _, session_path = swap_session_stack
        save_session(
            session_path,
            build_session_payload(
                auto_phase="wait_swap",
                sn="SN004",
                step1_done=True,
                step2_done=False,
                old_fingerprint=None,
                wait_new_started_at=None,
                last_export_bin=None,
                new_board_fru_backup_path=None,
            ),
        )
        controller.restore_session()
        host.questions[0][2](False)
        assert not Path(session_path).exists()


class TestSetSwapMode:
    def test_switch_to_auto_starts_sn_detect_when_online(self, swap_session_stack):
        controller, host, progress, workflow, _ = swap_session_stack
        controller.setSwapMode("auto")
        assert controller.swapMode == "auto"
        assert workflow.sn_detect_started is True

    def test_switch_to_manual_while_running_prompts(self, swap_session_stack):
        controller, host, _, _, _ = swap_session_stack
        controller._swap_auto.state.mode = "auto"
        controller._swap_auto.state.phase = "wait_swap"
        controller.setSwapMode("manual")
        assert len(host.questions) == 1
        assert controller.swapMode == "auto"
        host.questions[0][2](True)
        assert controller.swapMode == "manual"
