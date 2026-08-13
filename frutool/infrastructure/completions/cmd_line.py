"""Command-line tab completion and history navigation for the terminal input."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable

from frutool.infrastructure.completions.ipmi_completions import (
    _split_command_text,
    get_free_completions,
    get_ipmi_completions,
)


def _apply_match(text: str, match: str, *, trailing_space: bool = False) -> str:
    tokens, partial, completing_new = _split_command_text(text)
    if completing_new:
        prefix = text.rstrip()
        sep = " " if prefix else ""
        result = f"{prefix}{sep}{match}"
    elif partial:
        cut = text.rfind(partial)
        result = text[:cut] + match
    else:
        result = match
    if trailing_space and not result.endswith(" "):
        result += " "
    return result


@dataclass
class TabCompletionState:
    anchor: str = ""
    matches: list[str] = field(default_factory=list)
    index: int = -1

    def reset(self) -> None:
        self.anchor = ""
        self.matches = []
        self.index = -1


@dataclass
class CommandLineState:
    history: list[str] = field(default_factory=list)
    history_browse_index: int = -1
    history_draft: str = ""
    tab: TabCompletionState = field(default_factory=TabCompletionState)

    def reset_history_browse(self) -> None:
        self.history_browse_index = -1
        self.history_draft = ""

    def reset_tab(self) -> None:
        self.tab.reset()

    def append_history(self, command: str) -> None:
        if command not in self.history:
            self.history.append(command)
            if len(self.history) > 50:
                self.history.pop(0)

    def history_up(self, current: str) -> str:
        if not self.history:
            return current
        if self.history_browse_index == -1:
            self.history_draft = current
            self.history_browse_index = len(self.history)
        if self.history_browse_index > 0:
            self.history_browse_index -= 1
        return self.history[self.history_browse_index]

    def history_down(self, current: str) -> str:
        if self.history_browse_index == -1:
            return current
        if self.history_browse_index < len(self.history) - 1:
            self.history_browse_index += 1
            return self.history[self.history_browse_index]
        self.reset_history_browse()
        return self.history_draft


def complete_tab(text: str, matches: list[str], state: TabCompletionState) -> str:
    if not matches:
        state.reset()
        return text

    if state.matches and (text == state.anchor or _same_completion_context(text, state)):
        state.index = (state.index + 1) % len(state.matches)
        return _apply_match(text, state.matches[state.index], trailing_space=False)

    state.reset()

    if len(matches) == 1:
        return _apply_match(text, matches[0], trailing_space=True)

    _, partial, completing_new = _split_command_text(text)
    prefix = os.path.commonprefix(matches)
    if not completing_new and len(prefix) > len(partial):
        return _apply_match(text, prefix, trailing_space=False)

    state.anchor = text
    state.matches = matches
    state.index = 0
    return _apply_match(text, matches[0], trailing_space=False)


def _same_completion_context(text: str, state: TabCompletionState) -> bool:
    if not state.anchor or not state.matches:
        return False
    if text.startswith(state.anchor.rstrip()):
        return True
    anchor_tokens, anchor_partial, anchor_new = _split_command_text(state.anchor)
    text_tokens, text_partial, text_new = _split_command_text(text)
    if anchor_tokens != text_tokens:
        return False
    if anchor_new and text_new:
        return True
    if state.matches and text_partial:
        return any(m.lower().startswith(text_partial.lower()) for m in state.matches)
    return False


def make_completion_provider(mode: str, history: list[str]) -> Callable[[str], list[str]]:
    if mode == "IPMI模式":
        return get_ipmi_completions
    return lambda text: get_free_completions(text, history)
