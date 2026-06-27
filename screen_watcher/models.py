"""Domain models for Rule Engine + Notification.

Dataclasses thay vì Pydantic để giữ dependencies tối thiểu cho module này.
Config loader bên ngoài có thể wrap thêm Pydantic validation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class RuleType(str, Enum):
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX = "regex"
    ALL_KEYWORDS = "all_keywords"
    ANY_KEYWORDS = "any_keywords"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Rule:
    id: str
    name: str
    type: RuleType
    severity: Severity
    owner_group: str
    cooldown_minutes: int = 0

    # Một trong các field dưới đây sẽ được dùng tuỳ theo `type`
    keywords: List[str] = field(default_factory=list)
    pattern: Optional[str] = None
    ignore_case: bool = False

    def __post_init__(self) -> None:
        # Cho phép truyền type/severity dưới dạng string
        if isinstance(self.type, str):
            self.type = RuleType(self.type)
        if isinstance(self.severity, str):
            self.severity = Severity(self.severity)

        if self.type == RuleType.REGEX and not self.pattern:
            raise ValueError(f"Rule '{self.id}': type=regex yêu cầu 'pattern'")
        if self.type in (
            RuleType.CONTAINS,
            RuleType.NOT_CONTAINS,
            RuleType.ALL_KEYWORDS,
            RuleType.ANY_KEYWORDS,
        ) and not self.keywords:
            raise ValueError(
                f"Rule '{self.id}': type={self.type.value} yêu cầu 'keywords' không rỗng"
            )
        if self.cooldown_minutes < 0:
            raise ValueError(
                f"Rule '{self.id}': cooldown_minutes phải >= 0"
            )


@dataclass
class OwnerGroup:
    name: str
    emails: List[str]


@dataclass
class MatchResult:
    rule_id: str
    rule_name: str
    severity: Severity
    owner_group: str
    cooldown_minutes: int
    matched_text: str  # snippet hoặc full text dùng để trace
    matched_at: datetime = field(default_factory=datetime.now)


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    username: str
    from_address: str
    password: str = ""           # thực tế nên load từ env
    use_tls: bool = True
    timeout_seconds: int = 30
