"""Unit tests cho email_service.

Mock smtplib bằng cách inject một SMTP factory giả vào EmailService.
Không cần SMTP server thật.
"""
import smtplib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from screen_watcher.email_service import EmailSendError, EmailService
from screen_watcher.models import EmailConfig


def _make_smtp_mock():
    """Tạo một fake smtplib.SMTP class — instance là MagicMock với context manager."""
    smtp_instance = MagicMock()
    smtp_instance.__enter__ = MagicMock(return_value=smtp_instance)
    smtp_instance.__exit__ = MagicMock(return_value=False)
    factory = MagicMock(return_value=smtp_instance)
    return factory, smtp_instance


def _config(**overrides):
    defaults = dict(
        smtp_host="smtp.test",
        smtp_port=587,
        username="alert@test",
        from_address="alert@test",
        password="secret",
        use_tls=True,
        timeout_seconds=5,
    )
    defaults.update(overrides)
    return EmailConfig(**defaults)


class TestEmailServiceSend(unittest.TestCase):
    def test_send_calls_smtp_with_tls_and_login(self):
        factory, smtp = _make_smtp_mock()
        svc = EmailService(_config(), smtp_factory=factory)

        svc.send(
            subject="Subject",
            body="Hello",
            to=["a@test.com", "b@test.com"],
        )

        factory.assert_called_once_with("smtp.test", 587, timeout=5)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("alert@test", "secret")
        smtp.send_message.assert_called_once()

    def test_send_skips_tls_when_disabled(self):
        factory, smtp = _make_smtp_mock()
        svc = EmailService(_config(use_tls=False), smtp_factory=factory)
        svc.send(subject="s", body="b", to=["x@y"])
        smtp.starttls.assert_not_called()

    def test_send_skips_login_when_no_password(self):
        factory, smtp = _make_smtp_mock()
        svc = EmailService(_config(password=""), smtp_factory=factory)
        svc.send(subject="s", body="b", to=["x@y"])
        smtp.login.assert_not_called()

    def test_send_message_has_correct_headers(self):
        factory, smtp = _make_smtp_mock()
        svc = EmailService(_config(), smtp_factory=factory)
        svc.send(
            subject="[Alert] Disk full",
            body="Body content",
            to=["ops@co.com", "dba@co.com"],
        )
        msg = smtp.send_message.call_args[0][0]
        self.assertEqual(msg["Subject"], "[Alert] Disk full")
        self.assertEqual(msg["From"], "alert@test")
        self.assertEqual(msg["To"], "ops@co.com, dba@co.com")
        self.assertIn("Body content", msg.get_content())

    def test_empty_recipients_raises(self):
        factory, _ = _make_smtp_mock()
        svc = EmailService(_config(), smtp_factory=factory)
        with self.assertRaises(EmailSendError):
            svc.send(subject="s", body="b", to=[])

    def test_smtp_exception_wrapped(self):
        factory, smtp = _make_smtp_mock()
        smtp.send_message.side_effect = smtplib.SMTPException("boom")
        svc = EmailService(_config(), smtp_factory=factory)
        with self.assertRaises(EmailSendError):
            svc.send(subject="s", body="b", to=["x@y"])

    def test_oserror_wrapped(self):
        factory, smtp = _make_smtp_mock()
        smtp.send_message.side_effect = OSError("network down")
        svc = EmailService(_config(), smtp_factory=factory)
        with self.assertRaises(EmailSendError):
            svc.send(subject="s", body="b", to=["x@y"])


class TestEmailServiceAttachments(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.png = Path(self.tmp.name) / "screenshot.png"
        self.png.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-data")
        self.txt = Path(self.tmp.name) / "ocr.txt"
        self.txt.write_text("OCR result", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_attachments_included(self):
        factory, smtp = _make_smtp_mock()
        svc = EmailService(_config(), smtp_factory=factory)
        svc.send(
            subject="s",
            body="b",
            to=["x@y"],
            attachments=[str(self.png), str(self.txt)],
        )
        msg = smtp.send_message.call_args[0][0]
        names = [
            part.get_filename()
            for part in msg.iter_attachments()
        ]
        self.assertIn("screenshot.png", names)
        self.assertIn("ocr.txt", names)

    def test_missing_attachment_skipped_not_fatal(self):
        factory, smtp = _make_smtp_mock()
        svc = EmailService(_config(), smtp_factory=factory)
        svc.send(
            subject="s",
            body="b",
            to=["x@y"],
            attachments=["does-not-exist.png", str(self.txt)],
        )
        msg = smtp.send_message.call_args[0][0]
        names = [p.get_filename() for p in msg.iter_attachments()]
        self.assertEqual(names, ["ocr.txt"])


if __name__ == "__main__":
    unittest.main()
