"""Email service: build MIME message và gửi qua SMTP.

Tách rời khỏi rule engine để dễ thay backend (Slack, Teams) sau MVP.
"""
from __future__ import annotations

import logging
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable, List, Optional

from .models import EmailConfig

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Raised khi không gửi được email — caller quyết định retry hay log."""


class EmailService:
    def __init__(
        self,
        config: EmailConfig,
        smtp_factory=None,  # cho phép inject mock SMTP trong unit test
    ):
        self._config = config
        # Mặc định dùng smtplib.SMTP; test sẽ truyền factory mock vào.
        self._smtp_factory = smtp_factory or smtplib.SMTP

    def send(
        self,
        subject: str,
        body: str,
        to: Iterable[str],
        attachments: Optional[Iterable[str]] = None,
    ) -> None:
        recipients = [addr for addr in to if addr]
        if not recipients:
            raise EmailSendError("Không có recipient nào để gửi email")

        msg = self._build_message(subject, body, recipients, attachments or [])

        try:
            with self._smtp_factory(
                self._config.smtp_host,
                self._config.smtp_port,
                timeout=self._config.timeout_seconds,
            ) as smtp:
                if self._config.use_tls:
                    smtp.starttls()
                if self._config.username and self._config.password:
                    smtp.login(self._config.username, self._config.password)
                smtp.send_message(msg)
        except (smtplib.SMTPException, OSError) as exc:
            # Wrap để caller không phải biết về smtplib
            raise EmailSendError(str(exc)) from exc

        logger.info(
            "Email sent: subject=%r, to=%s, attachments=%d",
            subject,
            recipients,
            len(list(attachments or [])),
        )

    # ─── helpers ───────────────────────────────────────────────────────

    def _build_message(
        self,
        subject: str,
        body: str,
        recipients: List[str],
        attachments: Iterable[str],
    ) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self._config.from_address
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)

        for path_str in attachments:
            self._attach_file(msg, path_str)

        return msg

    @staticmethod
    def _attach_file(msg: EmailMessage, path_str: str) -> None:
        path = Path(path_str)
        if not path.is_file():
            logger.warning("Attachment không tồn tại, skip: %s", path)
            return
        ctype, _ = mimetypes.guess_type(str(path))
        maintype, subtype = (
            ctype.split("/", 1) if ctype else ("application", "octet-stream")
        )
        with path.open("rb") as fp:
            msg.add_attachment(
                fp.read(),
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )
