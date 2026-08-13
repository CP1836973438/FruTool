"""Terminal command line state: tab completion and history."""
from __future__ import annotations

from frutool.infrastructure.completions.cmd_line import CommandLineState, complete_tab, make_completion_provider


class TerminalService:
    def __init__(self) -> None:
        self._cmd_line = CommandLineState()

    def reset_tab(self) -> None:
        self._cmd_line.reset_tab()

    def reset_browse(self) -> None:
        self._cmd_line.reset_history_browse()
        self._cmd_line.reset_tab()

    def complete_tab(self, mode: str, text: str) -> str:
        provider = make_completion_provider(mode, self._cmd_line.history)
        matches = provider(text)
        return complete_tab(text, matches, self._cmd_line.tab)

    def history_up(self, current: str) -> str:
        return self._cmd_line.history_up(current)

    def history_down(self, current: str) -> str:
        return self._cmd_line.history_down(current)

    def record_command(self, cmd_str: str) -> None:
        if cmd_str not in self._cmd_line.history:
            self._cmd_line.append_history(cmd_str)
        self._cmd_line.reset_history_browse()
        self._cmd_line.reset_tab()
