"""Rule Engine: chấm điểm OCR text theo danh sách rule.

Pure logic — không phụ thuộc email, state, hay scheduler. Vì vậy rất dễ test.
"""
from __future__ import annotations

import logging
import re
from typing import Iterable, List

from .models import MatchResult, Rule, RuleType

logger = logging.getLogger(__name__)

# Giới hạn snippet text gắn vào MatchResult để log/email không bị phình.
_MATCHED_TEXT_LIMIT = 500


class RuleEngine:
    def __init__(self, rules: Iterable[Rule]):
        self._rules: List[Rule] = list(rules)

    @property
    def rules(self) -> List[Rule]:
        return list(self._rules)

    def evaluate(self, text: str) -> List[MatchResult]:
        """Chạy tất cả rule trên text. Trả về danh sách các rule matched."""
        results: List[MatchResult] = []
        if text is None:
            text = ""
        for rule in self._rules:
            try:
                if self._matches(rule, text):
                    results.append(
                        MatchResult(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            owner_group=rule.owner_group,
                            cooldown_minutes=rule.cooldown_minutes,
                            matched_text=text[:_MATCHED_TEXT_LIMIT],
                        )
                    )
            except re.error as exc:
                # regex sai cú pháp — log và bỏ qua rule này, không crash workflow
                logger.error("Rule '%s' regex invalid: %s", rule.id, exc)
        return results

    def _matches(self, rule: Rule, text: str) -> bool:
        haystack = text.lower() if rule.ignore_case else text

        if rule.type == RuleType.CONTAINS or rule.type == RuleType.ANY_KEYWORDS:
            return any(
                self._needle(kw, rule.ignore_case) in haystack
                for kw in rule.keywords
            )

        if rule.type == RuleType.ALL_KEYWORDS:
            return all(
                self._needle(kw, rule.ignore_case) in haystack
                for kw in rule.keywords
            )

        if rule.type == RuleType.NOT_CONTAINS:
            # Match khi text KHÔNG chứa bất kỳ keyword nào trong list
            return not any(
                self._needle(kw, rule.ignore_case) in haystack
                for kw in rule.keywords
            )

        if rule.type == RuleType.REGEX:
            flags = re.IGNORECASE if rule.ignore_case else 0
            return re.search(rule.pattern, text, flags=flags) is not None

        # Không nên xảy ra vì RuleType là Enum đóng
        raise ValueError(f"Unsupported rule type: {rule.type}")

    @staticmethod
    def _needle(kw: str, ignore_case: bool) -> str:
        return kw.lower() if ignore_case else kw
