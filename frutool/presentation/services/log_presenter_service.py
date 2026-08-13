"""Log line formatting for UI and file output (no Qt)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from frutool.infrastructure.log_util import classify_log
from frutool.theme.tokens import log_prefix

_MAC_RE = re.compile(
    r"([0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2})"
)


@dataclass(frozen=True)
class PreparedLogLine:
    short_ts: str
    full_ts: str
    tabs: tuple[str, ...]
    file_line: str
    last_plain: str
    mac: Optional[str]


def prepare_log_line(
    level: str,
    message: str,
    *,
    tab_override: Optional[str] = None,
    now: Optional[datetime] = None,
) -> PreparedLogLine:
    moment = now or datetime.now()
    short_ts = moment.strftime("%H:%M:%S")
    full_ts = moment.strftime("%Y-%m-%d %H:%M:%S")
    prefix = log_prefix(level)
    plain = message.replace("\n", " ")
    mac_match = _MAC_RE.search(message)
    if tab_override == "all":
        tabs = ("all",)
    elif tab_override:
        tabs = ("all", tab_override)
    else:
        tabs = tuple(classify_log(message))
    return PreparedLogLine(
        short_ts=short_ts,
        full_ts=full_ts,
        tabs=tabs,
        file_line=f"[{full_ts}] {prefix} {plain}",
        last_plain=f"[{short_ts}] {prefix} {plain}",
        mac=mac_match.group(1) if mac_match else None,
    )
