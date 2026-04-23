import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class OutputMarker:
    confidence_level: str
    confidence_score: float
    conflict_flags: list[dict]
    source_metadata: dict

    def to_dict(self):
        return asdict(self)


@dataclass
class AuditItem:
    request_id: str
    risk_level: str
    action_type: str
    description: str
    status: str
    created_at: str
    reviewed_at: Optional[str] = None
    reviewer: Optional[str] = None

    def to_dict(self):
        return asdict(self)


class Intervener:
    CONFIDENCE_THRESHOLDS = {"high": 0.8, "medium": 0.5, "low": 0.0}
    RISK_LEVELS = {"high": 1.0, "medium": 0.1, "low": 0.01}

    def __init__(self, observer=None, evaluator=None, decision_log=None):
        self.observer = observer
        self.evaluator = evaluator
        self.decision_log = decision_log
        self._circuit_open = False
        self._audit_queue = []
        self._rule_expiry_days = int(os.getenv("RULE_EXPIRY_DAYS", "30"))

    def mark_output(self, confidence_score: float, conflicts: Optional[list[dict]] = None,
                     source_meta: Optional[dict] = None) -> OutputMarker:
        if confidence_score >= self.CONFIDENCE_THRESHOLDS["high"]:
            level = "high"
        elif confidence_score >= self.CONFIDENCE_THRESHOLDS["medium"]:
            level = "medium"
        else:
            level = "low"

        return OutputMarker(
            confidence_level=level,
            confidence_score=confidence_score,
            conflict_flags=conflicts or [],
            source_metadata=source_meta or {},
        )

    def format_output(self, content: str, marker: OutputMarker) -> str:
        emoji = {"high": "\U0001F7E2", "medium": "\U0001F7E1", "low": "\U0001F534"}
        prefix = f"[{emoji.get(marker.confidence_level, '?')} {marker.confidence_level.upper()} confidence: {marker.confidence_score:.0%}]"

        result = f"{prefix}\n\n{content}"

        if marker.conflict_flags:
            result += "\n\n⚠️ Data Conflicts Detected:\n"
            for c in marker.conflict_flags:
                result += f"- {c.get('metric', 'unknown')}: {c.get('value_a', '?')} vs {c.get('value_b', '?')}\n"
                if c.get("recommendation"):
                    result += f"  Recommendation: {c['recommendation']}\n"

        return result

    def check_circuit_breaker(self, health_report: dict) -> bool:
        overall = health_report.get("overall_health", 100)
        threshold = float(os.getenv("CIRCUIT_BREAKER_HEALTH_THRESHOLD", "60"))

        if overall < threshold:
            self._trigger_circuit_breaker(f"Overall health {overall} < {threshold}")
            return True

        anomalies = health_report.get("anomalies", [])
        for a in anomalies:
            if a.get("severity") == "CRITICAL":
                self._trigger_circuit_breaker(f"Critical anomaly: {a.get('message')}")
                return True

        return False

    def _trigger_circuit_breaker(self, reason: str):
        self._circuit_open = True
        self._audit_queue.append(AuditItem(
            request_id=f"cb-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            risk_level="high",
            action_type="circuit_breaker",
            description=f"Circuit breaker triggered: {reason}",
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
        ))

    def reset_circuit_breaker(self):
        self._circuit_open = False

    def is_circuit_open(self) -> bool:
        return self._circuit_open

    def add_to_audit_queue(self, request_id: str, risk_level: str, action_type: str, description: str):
        sample_rate = self.RISK_LEVELS.get(risk_level, 0.01)
        import random
        if risk_level == "high" or random.random() < sample_rate:
            self._audit_queue.append(AuditItem(
                request_id=request_id,
                risk_level=risk_level,
                action_type=action_type,
                description=description,
                status="pending",
                created_at=datetime.now(timezone.utc).isoformat(),
            ))

    def get_audit_queue(self, status: str = "pending") -> list[dict]:
        return [item.to_dict() for item in self._audit_queue if item.status == status]

    def approve_audit_item(self, request_id: str, reviewer: str = "admin") -> bool:
        for item in self._audit_queue:
            if item.request_id == request_id:
                item.status = "approved"
                item.reviewed_at = datetime.now(timezone.utc).isoformat()
                item.reviewer = reviewer
                return True
        return False

    def reject_audit_item(self, request_id: str, reviewer: str = "admin") -> bool:
        for item in self._audit_queue:
            if item.request_id == request_id:
                item.status = "rejected"
                item.reviewed_at = datetime.now(timezone.utc).isoformat()
                item.reviewer = reviewer
                return True
        return False

    def check_rule_expiry(self, rules: list[dict]) -> list[dict]:
        now = datetime.now(timezone.utc)
        expired = []
        for rule in rules:
            updated = rule.get("updated_at", rule.get("created_at", ""))
            if updated:
                try:
                    updated_dt = datetime.fromisoformat(updated)
                    if (now - updated_dt).days > self._rule_expiry_days:
                        expired.append(rule["id"])
                except (ValueError, TypeError):
                    pass
        return expired

    def get_loop_break_report(self) -> dict:
        expired_rules = []
        audit_pending = len(self.get_audit_queue("pending"))
        return {
            "circuit_breaker_open": self._circuit_open,
            "expired_rules": expired_rules,
            "audit_queue_size": audit_pending,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
