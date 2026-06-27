"""State store cho cooldown.

MVP: JSON file. Nâng cấp tương lai: SQLite. Interface giữ nguyên.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_KEY_LAST_SENT = "last_sent_at"


class StateStore:
    def __init__(self, path: str | os.PathLike):
        self._path = Path(path)
        self._state: Dict[str, Dict[str, str]] = self._load()

    # ─── I/O ───────────────────────────────────────────────────────────

    def _load(self) -> Dict[str, Dict[str, str]]:
        if not self._path.exists():
            return {}
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning(
                    "State file %s không phải object — reset về rỗng", self._path
                )
                return {}
            return data
        except json.JSONDecodeError as exc:
            logger.error(
                "State file %s bị hỏng (%s) — reset về rỗng", self._path, exc
            )
            return {}

    def _flush(self) -> None:
        """Atomic write: ghi vào temp file rồi rename, tránh corrupt khi crash giữa chừng."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=".state-", suffix=".json", dir=str(self._path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, sort_keys=True)
            os.replace(tmp_path, self._path)
        except Exception:
            # Clean up nếu replace fail
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # ─── API ───────────────────────────────────────────────────────────

    def get_last_sent(self, rule_id: str) -> Optional[datetime]:
        entry = self._state.get(rule_id)
        if not entry:
            return None
        raw = entry.get(_KEY_LAST_SENT)
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            logger.warning(
                "Rule '%s' có last_sent_at không hợp lệ: %s", rule_id, raw
            )
            return None

    def is_in_cooldown(
        self, rule_id: str, cooldown_minutes: int, now: Optional[datetime] = None
    ) -> bool:
        if cooldown_minutes <= 0:
            return False
        last_sent = self.get_last_sent(rule_id)
        if last_sent is None:
            return False
        now = now or datetime.now()
        return (now - last_sent) < timedelta(minutes=cooldown_minutes)

    def mark_sent(self, rule_id: str, now: Optional[datetime] = None) -> None:
        ts = (now or datetime.now()).isoformat(timespec="seconds")
        self._state[rule_id] = {_KEY_LAST_SENT: ts}
        self._flush()
