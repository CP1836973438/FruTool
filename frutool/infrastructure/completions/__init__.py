"""Command-line tab completion for terminal input."""
from frutool.infrastructure.completions.cmd_line import (
    CommandLineState,
    TabCompletionState,
    complete_tab,
    make_completion_provider,
)
from frutool.infrastructure.completions.ipmi_completions import (
    IPMI_COMMAND_TREE,
    IPMI_TEMPLATES,
    get_free_completions,
    get_ipmi_completions,
)

__all__ = [
    "CommandLineState",
    "IPMI_COMMAND_TREE",
    "IPMI_TEMPLATES",
    "TabCompletionState",
    "complete_tab",
    "get_free_completions",
    "get_ipmi_completions",
    "make_completion_provider",
]
