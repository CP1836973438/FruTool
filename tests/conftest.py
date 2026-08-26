"""Shared fixtures and sample data for domain tests."""
from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, Optional

import pytest

# Must be set before PyQt6 initializes (offscreen for headless controller tests).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

SAMPLE_FRU_OUTPUT = """
FRU Device Description : Builtin FRU Device
 Board Mfg            : Intel
 Board Product        : S2600WT
 Board Serial         : BQWF123456
 Board Part Number    : YZMB-03296-10F
 Product Manufacturer : Intel
 Product Name         : S2600WTTR
 Product Serial       : SN123456789
"""

NEW_BOARD_FRU_OUTPUT = """
 Board Serial         : NEWBOARD99
 Product Serial       : SN999999999
 Product Name         : NewBoard
"""


@pytest.fixture
def log_collector() -> tuple[list[tuple[str, str]], Callable[[str, str], None]]:
    entries: list[tuple[str, str]] = []

    def log(level: str, message: str) -> None:
        entries.append((level, message))

    return entries, log


def make_run_ipmi_mock(
    *,
    fru_list_output: str = SAMPLE_FRU_OUTPUT,
    returncode: int = 0,
    on_read: Callable[[str], None] | None = None,
) -> Callable[..., tuple[int, str, str]]:
    """Return a run_ipmi replacement keyed by subcommand patterns."""

    def fake_run_ipmi(args_list: list[str], log_cb=None, timeout: int = 30):
        cmd = " ".join(args_list)
        if "fru list" in cmd:
            return returncode, fru_list_output if returncode == 0 else "", ""
        if "fru read" in cmd and returncode == 0:
            # args: ... fru read 0 <path>
            path = args_list[-1]
            if on_read:
                on_read(path)
            else:
                with open(path, "wb") as fh:
                    fh.write(b"\x00" * 256)
            return 0, "", ""
        if "fru print" in cmd:
            return 0, fru_list_output, ""
        if "fru write" in cmd:
            return 0, "", ""
        if "fru edit" in cmd:
            return 0, "", ""
        return returncode, "", "unknown command"

    return fake_run_ipmi


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.processEvents()


class FakeApplicationHost:
    """Minimal host stub for controller unit tests."""

    def __init__(self) -> None:
        from frutool.presentation.services import DialogService

        self.closing = False
        self.busy = False
        self.logs: list[tuple[str, str]] = []
        self.questions: list[tuple[str, str, Callable[[bool], None]]] = []
        self.warnings: list[tuple[str, str]] = []
        self.swap_auto = None
        self.dialog_service = DialogService()

    def log(self, level: str, message: str) -> None:
        self.logs.append((level, message))

    def request_question(
        self,
        title: str,
        message: str,
        callback: Callable[[bool], None],
        *,
        default_no: bool = False,
    ) -> None:
        self.questions.append((title, message, callback))

    def request_warning(self, title: str, message: str) -> None:
        self.warnings.append((title, message))


@pytest.fixture
def fake_host() -> FakeApplicationHost:
    return FakeApplicationHost()
