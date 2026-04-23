import pytest
import tempfile
import json
import shutil
from pathlib import Path
from rules.rule_injector import RuleInjector

RULES_PATH = Path(__file__).parent.parent / "rules" / "rules.json"


class TestRuleInjector:
    @pytest.fixture
    def injector(self):
        tmp = tempfile.mktemp(suffix=".json")
        shutil.copy(str(RULES_PATH), tmp)
        inj = RuleInjector(rules_path=tmp)
        yield inj
        Path(tmp).unlink(missing_ok=True)

    def test_load_rules(self, injector):
        rules = injector._rules
        assert len(rules) == 20

    def test_get_rules_for_point(self, injector):
        rules = injector.get_rules_for_point("email.analysis")
        assert len(rules) > 0
        assert all("email.analysis" in r["injection_points"] for r in rules)

    def test_inject_rules(self, injector):
        base = "Analyze this email."
        result = injector.inject(base, "email.analysis")
        assert "Behavior Rules" in result
        assert "email.analysis" in result

    def test_inject_no_rules_for_unknown_point(self, injector):
        base = "Test prompt"
        result = injector.inject(base, "nonexistent.point")
        assert result == base

    def test_rules_sorted_by_priority(self, injector):
        rules = injector.get_rules_for_point("email.analysis")
        priorities = [r["priority"] for r in rules]
        assert priorities == sorted(priorities, reverse=True)

    def test_add_rule(self, injector):
        new_rule = {
            "text": "Test rule",
            "injection_points": ["compose"],
            "priority": 3,
        }
        added = injector.add_rule(new_rule)
        assert added["id"].startswith("R-")
        assert injector.get_rules_for_point("compose")

    def test_disable_rule(self, injector):
        rules = injector.get_rules_for_point("compose")
        if rules:
            rule_id = rules[0]["id"]
            injector.disable_rule(rule_id)
            active = injector.get_rules_for_point("compose")
            assert not any(r["id"] == rule_id for r in active)

    def test_get_stats(self, injector):
        stats = injector.get_stats()
        assert stats["total"] >= 20
        assert "by_injection_point" in stats

    def test_all_injection_points_covered(self, injector):
        points = {"email.call1", "email.embed", "email.analysis",
                   "goals.creation", "goals.review", "goals.replan",
                   "qa.relevance", "qa.embed", "qa.answer", "compose"}
        stats = injector.get_stats()
        for point in points:
            assert stats["by_injection_point"][point] >= 0
