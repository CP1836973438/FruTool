"""Connection credential storage (English keys; QML may pass Chinese aliases)."""
from __future__ import annotations

from typing import Optional

CONN_FIELD_ALIASES: dict[str, str] = {
    "旧板账号": "old_user",
    "旧板密码": "old_password",
    "新板账号": "new_user",
    "新板密码": "new_password",
}

DEFAULT_CONN: dict[str, str] = {
    "old_user": "fault",
    "old_password": "",
    "new_user": "toutiao",
    "new_password": "toutiao!@#",
}


def normalize_conn_field(key: str) -> Optional[str]:
    if key in DEFAULT_CONN:
        return key
    return CONN_FIELD_ALIASES.get(key)


class ConnCredentials:
    def __init__(self) -> None:
        self._values = dict(DEFAULT_CONN)

    def get(self, key: str) -> str:
        field = normalize_conn_field(key)
        if field is None:
            return ""
        return self._values[field]

    def set(self, key: str, value: str) -> Optional[str]:
        field = normalize_conn_field(key)
        if field is None or self._values[field] == value:
            return None
        self._values[field] = value
        return field

    @property
    def old_user(self) -> str:
        return self._values["old_user"]

    @property
    def old_password(self) -> str:
        return self._values["old_password"]

    @property
    def new_user(self) -> str:
        return self._values["new_user"]

    @property
    def new_password(self) -> str:
        return self._values["new_password"]

    def for_board(self, use_new: bool) -> tuple[str, str]:
        if use_new:
            return self.new_user.strip(), self.new_password
        return self.old_user.strip(), self.old_password
