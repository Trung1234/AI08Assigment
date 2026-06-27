"""Unit tests cho rule_engine."""
import unittest

from screen_watcher.models import Rule, RuleType, Severity
from screen_watcher.rule_engine import RuleEngine


def _rule(**overrides):
    defaults = dict(
        id="r1",
        name="rule 1",
        type=RuleType.CONTAINS,
        severity=Severity.HIGH,
        owner_group="ops",
        cooldown_minutes=0,
        keywords=["Error"],
    )
    defaults.update(overrides)
    return Rule(**defaults)


class TestContainsRule(unittest.TestCase):
    def test_contains_match(self):
        engine = RuleEngine([_rule(keywords=["Error"])])
        result = engine.evaluate("System Error at 10:05")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].rule_id, "r1")

    def test_contains_no_match(self):
        engine = RuleEngine([_rule(keywords=["Error"])])
        self.assertEqual(engine.evaluate("All good."), [])

    def test_contains_is_case_sensitive_by_default(self):
        engine = RuleEngine([_rule(keywords=["ERROR"])])
        self.assertEqual(engine.evaluate("system error"), [])

    def test_contains_ignore_case(self):
        engine = RuleEngine([_rule(keywords=["ERROR"], ignore_case=True)])
        self.assertEqual(len(engine.evaluate("system error")), 1)


class TestAnyKeywordsRule(unittest.TestCase):
    def test_any_match_when_one_present(self):
        rule = _rule(type=RuleType.ANY_KEYWORDS, keywords=["Failed", "Timeout"])
        engine = RuleEngine([rule])
        self.assertEqual(len(engine.evaluate("Connection Timeout")), 1)

    def test_any_no_match(self):
        rule = _rule(type=RuleType.ANY_KEYWORDS, keywords=["Failed", "Timeout"])
        engine = RuleEngine([rule])
        self.assertEqual(engine.evaluate("OK"), [])


class TestAllKeywordsRule(unittest.TestCase):
    def test_all_match_only_when_all_present(self):
        rule = _rule(type=RuleType.ALL_KEYWORDS, keywords=["Daily Sync", "Failed"])
        engine = RuleEngine([rule])
        self.assertEqual(
            len(engine.evaluate("Daily Sync status: Failed at 10:00")),
            1,
        )

    def test_all_no_match_when_one_missing(self):
        rule = _rule(type=RuleType.ALL_KEYWORDS, keywords=["Daily Sync", "Failed"])
        engine = RuleEngine([rule])
        self.assertEqual(engine.evaluate("Daily Sync OK"), [])


class TestNotContainsRule(unittest.TestCase):
    def test_match_when_keyword_absent(self):
        rule = _rule(type=RuleType.NOT_CONTAINS, keywords=["Service Running"])
        engine = RuleEngine([rule])
        self.assertEqual(len(engine.evaluate("status unknown")), 1)

    def test_no_match_when_keyword_present(self):
        rule = _rule(type=RuleType.NOT_CONTAINS, keywords=["Service Running"])
        engine = RuleEngine([rule])
        self.assertEqual(engine.evaluate("Service Running OK"), [])


class TestRegexRule(unittest.TestCase):
    def test_regex_match(self):
        rule = _rule(
            type=RuleType.REGEX,
            keywords=[],
            pattern=r"(ERROR|FAILED|TIMEOUT)",
            ignore_case=True,
        )
        engine = RuleEngine([rule])
        self.assertEqual(len(engine.evaluate("system error here")), 1)

    def test_regex_no_match(self):
        rule = _rule(
            type=RuleType.REGEX,
            keywords=[],
            pattern=r"^FATAL:",
        )
        engine = RuleEngine([rule])
        self.assertEqual(engine.evaluate("INFO: All good"), [])

    def test_invalid_regex_does_not_crash(self):
        # Tạo rule với regex hợp lệ rồi force-corrupt sau __post_init__
        rule = _rule(type=RuleType.REGEX, keywords=[], pattern=r"valid")
        rule.pattern = r"(unclosed"
        engine = RuleEngine([rule])
        # Không raise — chỉ log error và bỏ qua rule
        self.assertEqual(engine.evaluate("anything"), [])


class TestMultipleRules(unittest.TestCase):
    def test_multiple_rules_can_all_match(self):
        rule_a = _rule(id="a", keywords=["Error"])
        rule_b = _rule(id="b", keywords=["Timeout"])
        engine = RuleEngine([rule_a, rule_b])
        results = engine.evaluate("Error and Timeout both here")
        ids = sorted(r.rule_id for r in results)
        self.assertEqual(ids, ["a", "b"])

    def test_matched_text_is_truncated(self):
        long_text = "Error " + ("x" * 1000)
        engine = RuleEngine([_rule(keywords=["Error"])])
        result = engine.evaluate(long_text)
        self.assertLessEqual(len(result[0].matched_text), 500)


class TestRuleValidation(unittest.TestCase):
    def test_regex_requires_pattern(self):
        with self.assertRaises(ValueError):
            Rule(
                id="x",
                name="x",
                type=RuleType.REGEX,
                severity=Severity.HIGH,
                owner_group="ops",
            )

    def test_keyword_rule_requires_keywords(self):
        with self.assertRaises(ValueError):
            Rule(
                id="x",
                name="x",
                type=RuleType.CONTAINS,
                severity=Severity.HIGH,
                owner_group="ops",
                keywords=[],
            )

    def test_negative_cooldown_rejected(self):
        with self.assertRaises(ValueError):
            Rule(
                id="x",
                name="x",
                type=RuleType.CONTAINS,
                severity=Severity.HIGH,
                owner_group="ops",
                keywords=["e"],
                cooldown_minutes=-1,
            )

    def test_string_enum_coercion(self):
        rule = Rule(
            id="x",
            name="x",
            type="contains",
            severity="critical",
            owner_group="ops",
            keywords=["e"],
        )
        self.assertEqual(rule.type, RuleType.CONTAINS)
        self.assertEqual(rule.severity, Severity.CRITICAL)


class TestEmptyText(unittest.TestCase):
    def test_empty_text_with_contains(self):
        engine = RuleEngine([_rule(keywords=["Error"])])
        self.assertEqual(engine.evaluate(""), [])

    def test_none_text_does_not_crash(self):
        engine = RuleEngine([_rule(keywords=["Error"])])
        self.assertEqual(engine.evaluate(None), [])

    def test_empty_text_with_not_contains_matches(self):
        rule = _rule(type=RuleType.NOT_CONTAINS, keywords=["Service Running"])
        engine = RuleEngine([rule])
        # Empty text KHÔNG chứa keyword → not_contains match
        self.assertEqual(len(engine.evaluate("")), 1)


if __name__ == "__main__":
    unittest.main()
