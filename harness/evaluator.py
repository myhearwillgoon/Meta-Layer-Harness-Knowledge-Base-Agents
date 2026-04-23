import re
import json
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class Conflict:
    conflict_type: str
    metric: str
    source_a: dict
    source_b: dict
    value_a: str
    value_b: str
    severity: str
    recommendation: str

    def to_dict(self):
        return asdict(self)


WEIGHT_CONFIGS = {
    "fact_query": {"authority": 0.3, "freshness": 0.5, "consistency": 0.2},
    "decision_rationale": {"authority": 0.6, "freshness": 0.2, "consistency": 0.2},
    "compliance_check": {"authority": 0.4, "freshness": 0.4, "consistency": 0.2},
}


class Evaluator:
    def __init__(self, numerical_threshold: float = 0.05):
        self.numerical_threshold = numerical_threshold
        self._conflicts = []
        self._impact_cache = {}

    def detect_numerical_conflict(self, source_a: dict, source_b: dict, metric: str) -> Optional[Conflict]:
        val_a = self._extract_number(source_a.get("value", ""))
        val_b = self._extract_number(source_b.get("value", ""))

        if val_a is None or val_b is None:
            return None

        if val_a == 0:
            diff_ratio = abs(val_b) if val_b != 0 else 0
        else:
            diff_ratio = abs(val_a - val_b) / abs(val_a)

        if diff_ratio > self.numerical_threshold:
            return Conflict(
                conflict_type="numerical",
                metric=metric,
                source_a=source_a,
                source_b=source_b,
                value_a=str(val_a),
                value_b=str(val_b),
                severity="HIGH" if diff_ratio > 0.10 else "MEDIUM",
                recommendation=f"Verify latest data. {metric} differs by {diff_ratio:.1%}",
            )
        return None

    def detect_semantic_conflict(self, statement_a: str, statement_b: str) -> Optional[Conflict]:
        contradictions = [
            ("approved", "rejected"),
            ("increase", "decrease"),
            ("buy", "sell"),
            ("bullish", "bearish"),
            ("high risk", "low risk"),
        ]
        a_lower = statement_a.lower()
        b_lower = statement_b.lower()

        for pos, neg in contradictions:
            if (pos in a_lower and neg in b_lower) or (neg in a_lower and pos in b_lower):
                return Conflict(
                    conflict_type="semantic",
                    metric="semantic_opinion",
                    source_a={"statement": statement_a},
                    source_b={"statement": statement_b},
                    value_a=statement_a,
                    value_b=statement_b,
                    severity="MEDIUM",
                    recommendation=f"Contradictory statements detected: '{pos}' vs '{neg}'",
                )
        return None

    def detect_temporal_conflict(self, event_a: dict, event_b: dict) -> Optional[Conflict]:
        date_a = event_a.get("date", "")
        date_b = event_b.get("date", "")
        if date_a and date_b and date_a > date_b:
            if event_a.get("supersedes", False):
                return None
            return Conflict(
                conflict_type="temporal",
                metric="timeline",
                source_a=event_a,
                source_b=event_b,
                value_a=date_a,
                value_b=date_b,
                severity="LOW",
                recommendation=f"Newer data ({date_a}) may supersede older data ({date_b})",
            )
        return None

    def detect_authority_conflict(self, source_a: dict, source_b: dict) -> Optional[Conflict]:
        auth_a = source_a.get("authority_score", 3)
        auth_b = source_b.get("authority_score", 3)
        if abs(auth_a - auth_b) >= 2:
            return Conflict(
                conflict_type="authority",
                metric="authority_mismatch",
                source_a=source_a,
                source_b=source_b,
                value_a=f"authority={auth_a}",
                value_b=f"authority={auth_b}",
                severity="MEDIUM",
                recommendation=f"Prefer higher authority source (score {max(auth_a, auth_b)})",
            )
        return None

    def calculate_confidence(self, authority: int, freshness: int, consistency: float,
                              query_type: str = "fact_query") -> float:
        weights = WEIGHT_CONFIGS.get(query_type, WEIGHT_CONFIGS["fact_query"])
        confidence = (
            weights["authority"] * (authority / 5.0) +
            weights["freshness"] * (freshness / 5.0) +
            weights["consistency"] * consistency
        )
        return round(min(max(confidence, 0.0), 1.0), 3)

    def analyze_impact(self, change_type: str, target_id: str, reference_graph: Optional[dict] = None) -> dict:
        cache_key = f"{change_type}:{target_id}"
        if cache_key in self._impact_cache:
            return self._impact_cache[cache_key]

        impact = {
            "change_type": change_type,
            "target_id": target_id,
            "affected_count": 0,
            "affected_items": [],
            "recovery_cost": "low",
            "risk_level": "low",
        }

        if reference_graph:
            affected = self._traverse_graph(target_id, reference_graph)
            impact["affected_count"] = len(affected)
            impact["affected_items"] = affected
            if len(affected) > 10:
                impact["recovery_cost"] = "high"
                impact["risk_level"] = "high"
            elif len(affected) > 3:
                impact["recovery_cost"] = "medium"
                impact["risk_level"] = "medium"

        self._impact_cache[cache_key] = impact
        return impact

    def get_all_conflicts(self) -> list[dict]:
        return [c.to_dict() for c in self._conflicts]

    def clear_conflicts(self):
        self._conflicts.clear()

    def _extract_number(self, text: str) -> Optional[float]:
        match = re.search(r"([\d.]+)%?", str(text))
        if match:
            return float(match.group(1))
        return None

    def _traverse_graph(self, node_id: str, graph: dict, visited: Optional[set] = None) -> list[str]:
        if visited is None:
            visited = set()
        if node_id in visited:
            return []
        visited.add(node_id)
        affected = [node_id]
        for neighbor in graph.get(node_id, []):
            affected.extend(self._traverse_graph(neighbor, graph, visited))
        return list(set(affected))
