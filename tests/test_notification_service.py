"""Unit tests cho notification_service.

Mock email service và state store để test orchestration logic độc lập.
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from screen_watcher.email_service import EmailSendError
from screen_watcher.models import MatchResult, OwnerGroup, Severity
from screen_watcher.notification_service import NotificationService


def _match(**overrides):
    defaults = dict(
        rule_id="r1",
        rule_name="Rule 1",
        severity=Severity.HIGH,
        owner_group="ops",
        cooldown_minutes=30,
        matched_text="Error: timeout",
    )
    defaults.update(overrides)
    return MatchResult(**defaults)


def _service(owner_groups=None, in_cooldown=False):
    if owner_groups is None:
        owner_groups = {
            "ops": OwnerGroup(name="ops", emails=["a@co.com", "b@co.com"]),
        }
    email = MagicMock()
    state = MagicMock()
    state.is_in_cooldown.return_value = in_cooldown
    svc = NotificationService(
        owner_groups=owner_groups,
        email_service=email,
        state_store=state,
        instance_id="ops-win-01",
    )
    return svc, email, state


class TestDispatchSuccess(unittest.TestCase):
    def test_email_sent_when_not_in_cooldown(self):
        svc, email, state = _service()
        now = datetime(2026, 6, 27, 10, 5, 0)

        outcomes = svc.dispatch([_match()], attachments=["shot.png"], now=now)

        self.assertEqual(len(outcomes), 1)
        outcome = outcomes[0]
        self.assertTrue(outcome.sent)
        self.assertIsNone(outcome.skipped_reason)
        self.assertEqual(outcome.recipients, ["a@co.com", "b@co.com"])

        email.send.assert_called_once()
        kwargs = email.send.call_args.kwargs
        self.assertIn("HIGH", kwargs["subject"])
        self.assertIn("Rule 1", kwargs["subject"])
        self.assertEqual(kwargs["to"], ["a@co.com", "b@co.com"])
        self.assertEqual(kwargs["attachments"], ["shot.png"])

        state.mark_sent.assert_called_once_with("r1", now=now)

    def test_email_body_contains_match_details(self):
        svc, email, _ = _service()
        now = datetime(2026, 6, 27, 10, 5, 0)
        svc.dispatch([_match(matched_text="Status: Failed")], now=now)
        body = email.send.call_args.kwargs["body"]
        self.assertIn("Rule 1", body)
        self.assertIn("HIGH", body)
        self.assertIn("Status: Failed", body)
        self.assertIn("ops-win-01", body)
        self.assertIn("2026-06-27T10:05:00", body)


class TestCooldown(unittest.TestCase):
    def test_skip_when_in_cooldown(self):
        svc, email, state = _service(in_cooldown=True)
        outcomes = svc.dispatch([_match()])

        self.assertFalse(outcomes[0].sent)
        self.assertEqual(outcomes[0].skipped_reason, "cooldown")
        email.send.assert_not_called()
        state.mark_sent.assert_not_called()

    def test_cooldown_check_uses_rule_cooldown_minutes(self):
        svc, email, state = _service()
        now = datetime(2026, 6, 27, 10, 5, 0)
        svc.dispatch([_match(cooldown_minutes=45)], now=now)
        state.is_in_cooldown.assert_called_once_with("r1", 45, now=now)


class TestOwnerResolution(unittest.TestCase):
    def test_skip_when_owner_group_missing(self):
        svc, email, state = _service(owner_groups={})
        outcomes = svc.dispatch([_match()])
        self.assertFalse(outcomes[0].sent)
        self.assertEqual(outcomes[0].skipped_reason, "no_owner")
        email.send.assert_not_called()
        state.mark_sent.assert_not_called()

    def test_skip_when_owner_group_empty_emails(self):
        svc, email, state = _service(
            owner_groups={"ops": OwnerGroup(name="ops", emails=[])}
        )
        outcomes = svc.dispatch([_match()])
        self.assertEqual(outcomes[0].skipped_reason, "no_owner")
        email.send.assert_not_called()


class TestEmailFailure(unittest.TestCase):
    def test_state_not_updated_when_send_fails(self):
        svc, email, state = _service()
        email.send.side_effect = EmailSendError("smtp 500")

        outcomes = svc.dispatch([_match()])

        self.assertFalse(outcomes[0].sent)
        self.assertEqual(outcomes[0].skipped_reason, "send_error")
        self.assertIn("smtp 500", outcomes[0].error)
        # Quan trọng: nếu gửi fail thì KHÔNG mark_sent → lần chạy sau retry
        state.mark_sent.assert_not_called()


class TestMultipleMatches(unittest.TestCase):
    def test_handles_mix_of_outcomes_independently(self):
        owners = {
            "ops": OwnerGroup(name="ops", emails=["o@co"]),
            # owner-group "dba" cố tình thiếu
        }
        email = MagicMock()
        state = MagicMock()
        # cooldown chỉ áp dụng cho r-cooldown
        state.is_in_cooldown.side_effect = lambda rid, cd, now=None: rid == "r-cooldown"

        svc = NotificationService(
            owner_groups=owners,
            email_service=email,
            state_store=state,
        )

        matches = [
            _match(rule_id="r-ok", owner_group="ops"),
            _match(rule_id="r-cooldown", owner_group="ops"),
            _match(rule_id="r-no-owner", owner_group="dba"),
        ]
        outcomes = svc.dispatch(matches)

        self.assertEqual(len(outcomes), 3)
        by_id = {o.rule_id: o for o in outcomes}
        self.assertTrue(by_id["r-ok"].sent)
        self.assertEqual(by_id["r-cooldown"].skipped_reason, "cooldown")
        self.assertEqual(by_id["r-no-owner"].skipped_reason, "no_owner")

        # Chỉ một email được gửi
        self.assertEqual(email.send.call_count, 1)
        state.mark_sent.assert_called_once_with("r-ok", now=unittest.mock.ANY)


class TestIntegrationWithRealStateStore(unittest.TestCase):
    """Test notification_service + state_store thật, chỉ mock email."""

    def test_second_dispatch_within_window_skipped(self):
        import tempfile
        from pathlib import Path

        from screen_watcher.state_store import StateStore

        with tempfile.TemporaryDirectory() as tmp:
            state = StateStore(Path(tmp) / "state.json")
            email = MagicMock()
            svc = NotificationService(
                owner_groups={
                    "ops": OwnerGroup(name="ops", emails=["o@co"]),
                },
                email_service=email,
                state_store=state,
            )

            t0 = datetime(2026, 6, 27, 10, 0, 0)
            outcomes1 = svc.dispatch([_match(cooldown_minutes=30)], now=t0)
            self.assertTrue(outcomes1[0].sent)

            # 10 phút sau, vẫn trong cooldown
            t1 = t0 + timedelta(minutes=10)
            outcomes2 = svc.dispatch([_match(cooldown_minutes=30)], now=t1)
            self.assertFalse(outcomes2[0].sent)
            self.assertEqual(outcomes2[0].skipped_reason, "cooldown")

            # 31 phút sau, ngoài cooldown
            t2 = t0 + timedelta(minutes=31)
            outcomes3 = svc.dispatch([_match(cooldown_minutes=30)], now=t2)
            self.assertTrue(outcomes3[0].sent)

            self.assertEqual(email.send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
