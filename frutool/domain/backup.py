"""FRU backup file helpers."""
from __future__ import annotations

import os

from frutool.config import BACKUP_DIR

def list_fru_backups_for_sn(sn: str) -> list[str]:
    sn = sn.strip()
    if not sn:
        return []
    try:
        names = os.listdir(BACKUP_DIR)
    except OSError:
        return []
    return sorted(name for name in names if _is_sn_fru_backup(name, sn))


def _is_sn_fru_backup(name: str, sn: str) -> bool:
    """Accept `{sn}.bin` (manual export) or `{sn}_*.bin` (tool export)."""
    if not name.endswith(".bin") or "NEW_ORIGINAL" in name:
        return False
    stem = name[:-4]
    return stem == sn or stem.startswith(sn + "_")

