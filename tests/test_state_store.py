"""Unit tests cho state_store (cooldown)."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from screen_watcher.state_store import StateStore


class TestStateStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_returns_empty(self):
        store = StateStore(self.path)
        self.assertIsNone(store.get_last_sent("any"))
        self.assertFalse(store.is_in_cooldown("any", 30))

    def test_mark_sent_persists(self):
        store = StateStore(self.path)
        now = datetime(2026, 6, 27, 10, 0, 0)
        store.mark_sent("rule1", now=now)

        # State file đã được flush
        self.assertTrue(self.path.exists())
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIn("rule1", data)

        # Khởi tạo store mới → load lại được
        store2 = StateStore(self.path)
        self.assertEqual(store2.get_last_sent("rule1"), now)

    def test_in_cooldown_within_window(self):
        store = StateStore(self.path)
        sent_at = datetime(2026, 6, 27, 10, 0, 0)
        store.mark_sent("rule1", now=sent_at)

        now = sent_at + timedelta(minutes=10)
        self.assertTrue(store.is_in_cooldown("rule1", 30, now=now))

    def test_not_in_cooldown_after_window(self):
        store = StateStore(self.path)
        sent_at = datetime(2026, 6, 27, 10, 0, 0)
        store.mark_sent("rule1", now=sent_at)

        now = sent_at + timedelta(minutes=31)
        self.assertFalse(store.is_in_cooldown("rule1", 30, now=now))

    def test_cooldown_zero_disabled(self):
        store = StateStore(self.path)
        store.mark_sent("rule1", now=datetime.now())
        self.assertFalse(store.is_in_cooldown("rule1", 0))

    def test_unknown_rule_not_in_cooldown(self):
        store = StateStore(self.path)
        self.assertFalse(store.is_in_cooldown("never_sent", 30))

    def test_corrupt_state_file_resets_gracefully(self):
        self.path.write_text("{not valid json", encoding="utf-8")
        store = StateStore(self.path)
        # Không crash — coi như state rỗng
        self.assertIsNone(store.get_last_sent("rule1"))

    def test_non_dict_state_file_resets_gracefully(self):
        self.path.write_text("[]", encoding="utf-8")
        store = StateStore(self.path)
        self.assertIsNone(store.get_last_sent("rule1"))

    def test_invalid_timestamp_ignored(self):
        self.path.write_text(
            json.dumps({"rule1": {"last_sent_at": "not-a-date"}}),
            encoding="utf-8",
        )
        store = StateStore(self.path)
        self.assertIsNone(store.get_last_sent("rule1"))
        self.assertFalse(store.is_in_cooldown("rule1", 30))

    def test_atomic_write_no_temp_left_behind(self):
        store = StateStore(self.path)
        store.mark_sent("rule1", now=datetime.now())
        siblings = [
            p.name for p in self.path.parent.iterdir() if p.name.startswith(".state-")
        ]
        self.assertEqual(siblings, [])


if __name__ == "__main__":
    unittest.main()
