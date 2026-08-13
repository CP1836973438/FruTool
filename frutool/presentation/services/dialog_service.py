"""Dialog payload and callback registry (no Qt)."""
from __future__ import annotations

import json
import uuid
from typing import Callable, Optional


class DialogService:
    def __init__(self) -> None:
        self._callbacks: dict[str, Callable[[bool], None]] = {}

    def prepare_payload(self, payload: dict, callback: Optional[Callable[[bool], None]] = None) -> str:
        if callback is not None:
            dialog_id = payload.setdefault("id", str(uuid.uuid4()))
            self._callbacks[dialog_id] = callback
        return json.dumps(payload, ensure_ascii=False)

    def respond(self, dialog_id: str, accepted: bool) -> None:
        callback = self._callbacks.pop(dialog_id, None)
        if callback:
            callback(accepted)

    def clear(self) -> None:
        self._callbacks.clear()
