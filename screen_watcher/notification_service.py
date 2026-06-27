"""NotificationService — orchestrate cooldown, owner resolution và email."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from .email_service import EmailSendError, EmailService
from .models import MatchResult, OwnerGroup

logger = logging.getLogger(__name__)


@dataclass
class DispatchOutcome:
    rule_id: str
    sent: bool
    skipped_reason: Optional[str] = None  # cooldown / no_owner / send_error
    recipients: Optional[List[str]] = None
    error: Optional[str] = None


class NotificationService:
    def __init__(
        self,
        owner_groups: Dict[str, OwnerGroup],
        email_service: EmailService,
        state_store,
        instance_id: str = "screen-watcher",
    ):
        self._owners = owner_groups
        self._email = email_service
        self._state = state_store
        self._instance_id = instance_id

    def dispatch(
        self,
        matches: Iterable[MatchResult],
        attachments: Optional[List[str]] = None,
        now: Optional[datetime] = None,
    ) -> List[DispatchOutcome]:
        outcomes: List[DispatchOutcome] = []
        now = now or datetime.now()

        for match in matches:
            outcomes.append(self._dispatch_one(match, attachments or [], now))
        return outcomes

    # ─── internals ─────────────────────────────────────────────────────

    def _dispatch_one(
        self,
        match: MatchResult,
        attachments: List[str],
        now: datetime,
    ) -> DispatchOutcome:
        # 1. Cooldown check
        if self._state.is_in_cooldown(match.rule_id, match.cooldown_minutes, now=now):
            logger.info(
                "Skip rule '%s' — in cooldown (%d min)",
                match.rule_id,
                match.cooldown_minutes,
            )
            return DispatchOutcome(
                rule_id=match.rule_id,
                sent=False,
                skipped_reason="cooldown",
            )

        # 2. Resolve owner emails
        group = self._owners.get(match.owner_group)
        recipients = group.emails if group else []
        if not recipients:
            logger.warning(
                "Skip rule '%s' — owner_group '%s' không có email",
                match.rule_id,
                match.owner_group,
            )
            return DispatchOutcome(
                rule_id=match.rule_id,
                sent=False,
                skipped_reason="no_owner",
            )

        # 3. Build subject + body và gửi
        subject = self._build_subject(match)
        body = self._build_body(match, now)
        try:
            self._email.send(
                subject=subject,
                body=body,
                to=recipients,
                attachments=attachments,
            )
        except EmailSendError as exc:
            logger.error("Send email failed for rule '%s': %s", match.rule_id, exc)
            # Không update state → lần chạy sau sẽ retry
            return DispatchOutcome(
                rule_id=match.rule_id,
                sent=False,
                skipped_reason="send_error",
                recipients=recipients,
                error=str(exc),
            )

        # 4. Update cooldown state
        self._state.mark_sent(match.rule_id, now=now)
        return DispatchOutcome(
            rule_id=match.rule_id,
            sent=True,
            recipients=recipients,
        )

    def _build_subject(self, match: MatchResult) -> str:
        sev = match.severity.value.upper()
        return f"[Screen Watcher][{sev}] {match.rule_name}"

    def _build_body(self, match: MatchResult, now: datetime) -> str:
        return (
            f"Rule matched: {match.rule_name}\n"
            f"Severity: {match.severity.value.upper()}\n"
            f"Detected at: {now.isoformat(timespec='seconds')}\n"
            f"Instance: {self._instance_id}\n"
            f"\n"
            f"Matched text:\n"
            f"{match.matched_text}\n"
            f"\n"
            f"Action: Please check the dashboard or related batch job.\n"
        )
