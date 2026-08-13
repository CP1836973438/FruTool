"""Streaming shell command execution with cooperative cancel."""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from typing import Callable, MutableSequence, Optional

from frutool.config import LogCallback


def kill_process_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            creationflags=flags,
        )
    else:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


def _stream_lines(pipe, level: str, log: LogCallback, stop_event: threading.Event) -> None:
    try:
        for line in iter(pipe.readline, ""):
            if stop_event.is_set():
                break
            text = line.rstrip("\r\n")
            if text:
                log(level, text)
    finally:
        pipe.close()


def run_shell_command(
    cmd_str: str,
    log: LogCallback,
    *,
    cwd: str,
    creationflags: int,
    stop_event: threading.Event,
    proc_holder: MutableSequence[Optional[subprocess.Popen]],
) -> dict:
    log("cmd", cmd_str)
    proc = subprocess.Popen(
        cmd_str,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        cwd=cwd,
        creationflags=creationflags,
        bufsize=1,
    )
    proc_holder[:] = [proc]
    threads = [
        threading.Thread(target=_stream_lines, args=(proc.stdout, "info", log, stop_event), daemon=True),
        threading.Thread(target=_stream_lines, args=(proc.stderr, "warning", log, stop_event), daemon=True),
    ]
    for thread in threads:
        thread.start()

    interrupted = False
    try:
        while proc.poll() is None:
            if stop_event.is_set():
                interrupted = True
                kill_process_tree(proc)
                proc.wait(timeout=5)
                break
            time.sleep(0.05)
        else:
            for thread in threads:
                thread.join(timeout=2)
    finally:
        proc_holder[:] = []

    if interrupted or stop_event.is_set():
        log("warning", "Command interrupted (Ctrl+C)")
        return {"ok": False, "interrupted": True}

    code = proc.returncode if proc.returncode is not None else -1
    log("success" if code == 0 else "error", f"Return code: {code}")
    return {"ok": code == 0}
