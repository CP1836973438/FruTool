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
    return sorted(
        name
        for name in names
        if name.startswith(sn + "_") and "NEW_ORIGINAL" not in name and name.endswith(".bin")
    )
