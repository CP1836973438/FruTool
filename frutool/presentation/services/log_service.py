"""File-backed session logging (no Qt)."""
from __future__ import annotations

import os
from datetime import datetime
from typing import BinaryIO, Optional

from frutool.config import LOG_DIR


class LogService:
    def __init__(self) -> None:
        self._log_file_date: Optional[str] = None
        self._file: Optional[BinaryIO] = None

    def init_session(self) -> str:
        today = datetime.now().strftime("%Y%m%d")
        path = os.path.join(LOG_DIR, f"{today}.log")
        self._log_file_date = today
        self._file = open(path, "a", encoding="utf-8")
        self._write_header("SESSION START")
        self._file.flush()
        return path

    def write_line(self, line: str) -> None:
        self._ensure_file()
        if self._file:
            self._file.write(line + "\n")
            self._file.flush()

    def close(self, *, write_end: bool = True) -> None:
        if not self._file:
            return
        try:
            if write_end:
                self._file.write(f"SESSION END  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self._file.flush()
            self._file.close()
        except OSError:
            pass
        self._file = None

    def _ensure_file(self) -> None:
        today = datetime.now().strftime("%Y%m%d")
        if self._log_file_date == today and self._file is not None:
            return
        if self._file:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None
        path = os.path.join(LOG_DIR, f"{today}.log")
        self._log_file_date = today
        self._file = open(path, "a", encoding="utf-8")
        self._write_header("DAY ROLLOVER")
        self._file.flush()

    def _write_header(self, label: str) -> None:
        if not self._file:
            return
        path = os.path.join(LOG_DIR, f"{self._log_file_date}.log")
        self._file.write(f"\n{'=' * 60}\n")
        self._file.write(f"{label}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  PID={os.getpid()}\n")
        self._file.write(f"Log file: {path}\n")
        self._file.write(f"{'=' * 60}\n")
