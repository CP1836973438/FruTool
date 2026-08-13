"""Shell command execution state (no Qt)."""
from __future__ import annotations

import subprocess
import threading
from typing import Optional

from frutool.config import BASE_DIR, LogCallback
from frutool.infrastructure.network import _startup_flags
from frutool.infrastructure.shell_runner import kill_process_tree, run_shell_command


class ShellService:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._proc_holder: list[subprocess.Popen] = []
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def begin(self) -> tuple[threading.Event, list[subprocess.Popen]]:
        self._stop_event.clear()
        self._running = True
        return self._stop_event, self._proc_holder

    def finish(self) -> None:
        self._running = False
        self._stop_event.clear()
        self._proc_holder.clear()

    def interrupt(self) -> bool:
        if not self._running:
            return False
        self._stop_event.set()
        if self._proc_holder:
            kill_process_tree(self._proc_holder[0])
        return True

    def run_job(self, cmd_str: str, log: LogCallback):
        return run_shell_command(
            cmd_str,
            log,
            cwd=BASE_DIR,
            creationflags=_startup_flags(),
            stop_event=self._stop_event,
            proc_holder=self._proc_holder,
        )
