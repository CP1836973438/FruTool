"""IPMI and shell command completion data for the command-line input."""
from __future__ import annotations

import shlex
from typing import Any

_CHASSIS_POWER: dict[str, Any] = {
    "status": {},
    "on": {},
    "off": {},
    "cycle": {},
    "reset": {},
    "soft": {},
    "diag": {},
}

_CHASSIS_POLICY: dict[str, Any] = {
    "list": {},
    "always-on": {},
    "previous": {},
    "always-off": {},
}

_CHASSIS_BOOTDEV: dict[str, Any] = {
    "none": {},
    "pxe": {},
    "disk": {},
    "safe": {},
    "diag": {},
    "cdrom": {},
    "bios": {},
    "floppy": {},
}

_MC_RESET: dict[str, Any] = {
    "warm": {},
    "cold": {},
}

_MC_WATCHDOG: dict[str, Any] = {
    "get": {},
    "reset": {},
    "off": {},
}

_SEL_TIME: dict[str, Any] = {
    "get": {},
    "set": {},
}

_FRU_EDIT_FIELD: dict[str, Any] = {
    "c": {},
    "b": {},
    "p": {},
}

_FRU_ID: dict[str, Any] = {
    "0": {},
}

IPMI_COMMAND_TREE: dict[str, Any] = {
    "channel": {
        "info": {},
        "getaccess": {},
        "setaccess": {},
        "authcap": {},
        "getciphers": {},
    },
    "chassis": {
        "status": {},
        "power": _CHASSIS_POWER,
        "identify": {},
        "policy": _CHASSIS_POLICY,
        "bootdev": _CHASSIS_BOOTDEV,
        "selftest": {},
        "poh": {},
        "restart_cause": {},
        "bootparam": {},
    },
    "dcmi": {
        "discover": {},
        "power": {},
        "sensors": {},
        "asset": {},
        "get_mc_id_string": {},
        "set_mc_id_string": {},
    },
    "delloem": {},
    "echo": {},
    "event": {
        "file": {},
        "help": {},
    },
    "exec": {},
    "firewall": {},
    "fru": {
        "print": _FRU_ID,
        "list": _FRU_ID,
        "read": _FRU_ID,
        "write": _FRU_ID,
        "edit": {
            "0": {
                "field": _FRU_EDIT_FIELD,
                "oem": {},
            },
        },
        "upgEkey": _FRU_ID,
    },
    "fwum": {},
    "gendev": {
        "list": {},
        "read": {},
        "write": {},
    },
    "hpm": {},
    "i2c": {},
    "ime": {},
    "isol": {},
    "kontronoem": {},
    "lan": {
        "print": {},
        "set": {},
        "alert": {},
        "stats": {},
    },
    "mc": {
        "info": {},
        "reset": _MC_RESET,
        "guid": {},
        "selftest": {},
        "getenables": {},
        "setenables": {},
        "watchdog": _MC_WATCHDOG,
    },
    "bmc": {
        "info": {},
        "reset": _MC_RESET,
        "guid": {},
        "selftest": {},
        "getenables": {},
        "setenables": {},
        "watchdog": _MC_WATCHDOG,
    },
    "nm": {},
    "pef": {
        "info": {},
        "list": {},
        "status": {},
        "policy": {},
        "filter": {},
        "action": {},
    },
    "picmg": {},
    "power": _CHASSIS_POWER,
    "raw": {},
    "sdr": {
        "list": {},
        "elist": {},
        "get": {},
        "info": {},
        "type": {},
        "entity": {},
        "dump": {},
        "fill": {},
    },
    "sel": {
        "list": {},
        "elist": {},
        "info": {},
        "clear": {},
        "get": {},
        "delete": {},
        "save": {},
        "add": {},
        "writeraw": {},
        "readraw": {},
        "time": _SEL_TIME,
    },
    "sensor": {
        "list": {},
        "get": {},
        "thresh": {},
    },
    "session": {
        "info": {},
    },
    "set": {},
    "shell": {},
    "sol": {
        "info": {},
        "activate": {},
        "deactivate": {},
        "set": {},
        "payload": {},
    },
    "spd": {},
    "sunoem": {},
    "tsol": {},
    "user": {
        "list": {},
        "summary": {},
        "test": {},
        "set": {},
        "enable": {},
        "disable": {},
        "priv": {},
    },
    "ekanalyzer": {},
    "help": {},
}

IPMI_TEMPLATES: list[str] = [
    "fru list 0",
    "fru print 0",
    "fru read 0 ",
    "fru write 0 ",
    "fru edit 0 field b 2 ",
    "fru edit 0 field c 0 ",
    "fru edit 0 field p 0 ",
    "chassis power status",
    "chassis power on",
    "chassis power off",
    "chassis power cycle",
    "chassis power reset",
    "chassis status",
    "sdr elist",
    "sdr list",
    "sel elist",
    "sel list",
    "sel info",
    "sensor list",
    "mc info",
    "mc selftest",
    "lan print",
    "user list",
    "user summary",
]

IPMI_PRIORITY_COMMANDS: list[str] = [
    "fru",
    "chassis",
    "sdr",
    "sel",
    "sensor",
    "mc",
    "power",
    "lan",
    "user",
    "channel",
    "raw",
    "sol",
    "session",
    "event",
    "pef",
]


def _priority_sort_key(name: str) -> tuple[int, str]:
    try:
        return (IPMI_PRIORITY_COMMANDS.index(name), name.lower())
    except ValueError:
        return (len(IPMI_PRIORITY_COMMANDS), name.lower())


SHELL_COMMANDS: list[str] = [
    "cd",
    "copy",
    "del",
    "dir",
    "echo",
    "ipconfig",
    "move",
    "ping",
    "powershell",
    "python",
    "py",
    "type",
    "where",
    "whoami",
    "netstat",
    "tasklist",
    "taskkill",
    "systeminfo",
    "hostname",
    "cls",
    "exit",
]


def _split_command_text(text: str) -> tuple[list[str], str, bool]:
    """Return complete tokens, partial prefix, and whether completing a new token after whitespace."""
    stripped = text
    completing_new = stripped.endswith(" ") or not stripped
    try:
        tokens = shlex.split(stripped, posix=False)
    except ValueError:
        tokens = stripped.split()
    if completing_new:
        return tokens, "", True
    if not tokens:
        return [], "", False
    partial = tokens[-1]
    return tokens[:-1], partial, False


def _walk_tree(tokens: list[str]) -> dict[str, Any] | None:
    node: dict[str, Any] = IPMI_COMMAND_TREE
    for token in tokens:
        if not isinstance(node, dict) or token not in node:
            return None
        node = node[token]
    return node if isinstance(node, dict) else None


def _template_next_tokens(text: str) -> list[str]:
    prefix = text.rstrip()
    if not prefix:
        return []
    results: list[str] = []
    for template in IPMI_TEMPLATES:
        if not template.startswith(prefix):
            continue
        rest = template[len(prefix) :]
        if not rest or rest[0] != " ":
            continue
        next_word = rest.strip().split()[0]
        if next_word and next_word not in results:
            results.append(next_word)
    return results


def _filter_candidates(candidates: list[str], partial: str) -> list[str]:
    if not partial:
        filtered = set(candidates)
    else:
        lower = partial.lower()
        filtered = {c for c in candidates if c.lower().startswith(lower)}
    return sorted(filtered, key=_priority_sort_key)


def get_ipmi_completions(text: str) -> list[str]:
    """Return next-token candidates for partial IPMI command input."""
    tokens, partial, completing_new = _split_command_text(text)
    node = _walk_tree(tokens)
    if node is not None and not node:
        return []

    candidates: list[str] = []
    if node is not None and node:
        candidates.extend(node.keys())
    elif not tokens:
        candidates.extend(IPMI_COMMAND_TREE.keys())

    if completing_new:
        template_prefix = text
    elif partial:
        cut = text.rfind(partial)
        template_prefix = text[:cut]
    else:
        template_prefix = text
    candidates.extend(_template_next_tokens(template_prefix))

    return _filter_candidates(candidates, partial)


def get_free_completions(text: str, history: list[str]) -> list[str]:
    """Return next-token candidates for free-form shell command input."""
    tokens, partial, _completing_new = _split_command_text(text)
    candidates: list[str] = []

    if not tokens:
        candidates.extend(SHELL_COMMANDS)
        for entry in reversed(history):
            first = entry.split()[0] if entry.split() else entry
            if first:
                candidates.append(first)
    else:
        for entry in reversed(history):
            entry_tokens, entry_partial, entry_new = _split_command_text(entry)
            if len(entry_tokens) < len(tokens):
                continue
            if entry_tokens[: len(tokens) - 1] != tokens[:-1]:
                continue
            if entry_new and len(entry_tokens) == len(tokens):
                candidates.append(entry_tokens[-1])
            elif len(entry_tokens) > len(tokens) and entry_tokens[: len(tokens)] == tokens:
                candidates.append(entry_tokens[len(tokens)])

    return _filter_candidates(candidates, partial)
