"""GPU / Qt Quick rendering policy (survives Windows UAC relaunch)."""
from __future__ import annotations

import os
import sys

_FLAG = "--no-gpu-effects"
_shader_effects_enabled = True


def shader_effects_enabled() -> bool:
    return _shader_effects_enabled


def configure_startup(argv: list[str] | None = None) -> list[str]:
    """Parse flags/env before Qt starts; ensure flags survive UAC relaunch."""
    global _shader_effects_enabled

    args = list(argv if argv is not None else sys.argv)
    cleaned: list[str] = []
    for arg in args:
        if arg == _FLAG:
            _shader_effects_enabled = False
            continue
        if arg.startswith(f"{_FLAG}="):
            _shader_effects_enabled = arg.split("=", 1)[1].strip().lower() not in (
                "0",
                "false",
                "no",
            )
            continue
        cleaned.append(arg)

    env_disable = os.environ.get("FRUTOOL_DISABLE_GPU_EFFECTS", "").strip().lower()
    if env_disable in ("1", "true", "yes"):
        _shader_effects_enabled = False
    elif env_disable in ("0", "false", "no"):
        _shader_effects_enabled = True

    if not _shader_effects_enabled and _FLAG not in cleaned:
        cleaned.append(_FLAG)

    return cleaned
