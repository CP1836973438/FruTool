"""Tests for auto swap phase status text."""
from __future__ import annotations

from frutool.domain.swap.status import auto_phase_status, auto_phase_status_en


class TestAutoPhaseStatus:
    def test_idle_status(self):
        assert "BMC" in auto_phase_status("idle")

    def test_idle_status_en(self):
        assert "BMC" in auto_phase_status_en("idle")

    def test_wait_new_custom_text(self):
        assert auto_phase_status("wait_new", wait_new_text="custom") == "custom"

    def test_wait_new_custom_text_en(self):
        assert auto_phase_status_en("wait_new", wait_new_text="custom en") == "custom en"

    def test_wait_new_default(self):
        assert "旧板已离线" in auto_phase_status("wait_new")

    def test_wait_new_default_en(self):
        assert "Old board offline" in auto_phase_status_en("wait_new")

    def test_unknown_phase_empty(self):
        assert auto_phase_status("unknown_phase_xyz") == ""
