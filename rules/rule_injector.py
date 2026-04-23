import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


VALID_INJECTION_POINTS = {
    "email.call1", "email.embed", "email.analysis",
    "goals.creation", "goals.review", "goals.replan",
    "qa.relevance", "qa.embed", "qa.answer",
    "compose",
}


class RuleInjector:
    def __init__(self, rules_path: str, observer=None):
        self.rules_path = Path(rules_path)
        self.observer = observer
        self._rules = self._load_rules()

    def _load_rules(self) -> list[dict]:
        if not self.rules_path.exists():
            return []
        data = json.loads(self.rules_path.read_text(encoding="utf-8"))
        return data.get("rules", [])

    def reload(self):
        self._rules = self._load_rules()

    def get_rules_for_point(self, injection_point: str) -> list[dict]:
        if injection_point not in VALID_INJECTION_POINTS:
            return []
        return sorted(
            [r for r in self._rules if r.get("enabled", True) and injection_point in r.get("injection_points", [])],
            key=lambda r: r.get("priority", 0),
            reverse=True,
        )

    def inject(self, base_prompt: str, injection_point: str, context: Optional[dict] = None) -> str:
        rules = self.get_rules_for_point(injection_point)
        if not rules:
            return base_prompt

        injected = f"\n# Behavior Rules (injection point: {injection_point})\n\n"
        for rule in rules:
            injected += f"## {rule['id']} (priority: {rule['priority']})\n{rule['text']}\n\n"

        if self.observer:
            self.observer.record_rule_injection(
                injection_point=injection_point,
                rules_injected=[r["id"] for r in rules],
                injection_reason=context.get("trigger", "") if context else "",
                impact_scope=context.get("impact", "") if context else "",
            )

        return base_prompt + injected

    def add_rule(self, rule: dict) -> dict:
        rule.setdefault("id", f"R-{len(self._rules) + 1:03d}")
        rule.setdefault("priority", 3)
        rule.setdefault("source", "learned")
        rule.setdefault("enabled", True)
        now = datetime.now(timezone.utc).isoformat()
        rule.setdefault("created_at", now)
        rule.setdefault("updated_at", now)

        self._rules.append(rule)
        self._save_rules()
        return rule

    def update_rule(self, rule_id: str, updates: dict) -> Optional[dict]:
        for r in self._rules:
            if r["id"] == rule_id:
                r.update(updates)
                r["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_rules()
                return r
        return None

    def disable_rule(self, rule_id: str) -> bool:
        return self.update_rule(rule_id, {"enabled": False}) is not None

    def delete_rule(self, rule_id: str) -> bool:
        before = len(self._rules)
        self._rules = [r for r in self._rules if r["id"] != rule_id]
        if len(self._rules) < before:
            self._save_rules()
            return True
        return False

    def _save_rules(self):
        data = {"version": "1.0.0", "rules": self._rules, "metadata": {"total_rules": len(self._rules)}}
        self.rules_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def get_stats(self) -> dict:
        by_point = {}
        for point in VALID_INJECTION_POINTS:
            rules = self.get_rules_for_point(point)
            by_point[point] = len(rules)
        return {
            "total": len(self._rules),
            "enabled": sum(1 for r in self._rules if r.get("enabled", True)),
            "disabled": sum(1 for r in self._rules if not r.get("enabled", True)),
            "by_injection_point": by_point,
        }
