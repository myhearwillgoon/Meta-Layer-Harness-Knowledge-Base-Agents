import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


class Observer:
    def __init__(self, log_path: str = "logs/observations/"):
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self._loop_health_data = []
        self._knowledge_write_count = 0
        self._goal_completion_count = 0
        self._rule_injection_log = []
        self._user_corrections = []

    def record_knowledge_metadata(self, file_path: str, metadata: dict):
        self._write_observation("knowledge_metadata", {
            "file_path": file_path,
            "source_type": metadata.get("source_type", ""),
            "authority_score": metadata.get("authority_score", 3),
            "freshness_score": metadata.get("freshness_score", 3),
            "conflict_flag": metadata.get("conflict_flag", False),
        })

    def record_communication_metadata(self, channel_type: str, participants: list[str],
                                       urgency: str = "normal", sentiment: str = "neutral"):
        self._write_observation("communication_metadata", {
            "channel_type": channel_type,
            "participants": participants,
            "urgency": urgency,
            "sentiment_analysis": sentiment,
        })

    def record_prompt_assembly(self, stage: str, model: str, token_usage: dict,
                                sources: Optional[list[dict]] = None, rules_injected: Optional[list[str]] = None):
        import hashlib
        prompt_data = {
            "stage": stage,
            "model": model,
            "token_usage": token_usage,
            "sources": sources or [],
            "rules_injected": rules_injected or [],
        }
        prompt_hash = hashlib.sha256(json.dumps(prompt_data, sort_keys=True).encode()).hexdigest()[:16]
        prompt_data["prompt_hash"] = f"sha256:{prompt_hash}"
        self._write_observation("prompt_assembly", prompt_data)

    def record_rule_injection(self, injection_point: str, rules_injected: list[str],
                               injection_reason: str = "", impact_scope: str = ""):
        record = {
            "injection_point": injection_point,
            "rule_ids": rules_injected,
            "injection_reason": injection_reason,
            "impact_scope": impact_scope,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._rule_injection_log.append(record)
        self._write_observation("rule_injection", record)

    def record_loop_health(self, metrics: dict):
        self._loop_health_data.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **metrics,
        })

    def record_user_correction(self, draft_id: str, original: str, user_edit: str, diff: list[dict]):
        record = {
            "draft_id": draft_id,
            "original": original[:500],
            "user_edit": user_edit[:500],
            "diff": diff[:20],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._user_corrections.append(record)
        self._write_observation("user_correction", record)

    def record_knowledge_write(self):
        self._knowledge_write_count += 1

    def record_goal_completion(self):
        self._goal_completion_count += 1

    def get_loop_health_report(self) -> dict:
        loop_a = self._calculate_rule_health()
        loop_b = self._calculate_knowledge_health()
        loop_c = self._calculate_goal_health()

        overall = (loop_a["health_score"] + loop_b["health_score"] + loop_c["health_score"]) / 3

        return {
            "loop_a": loop_a,
            "loop_b": loop_b,
            "loop_c": loop_c,
            "overall_health": round(overall, 1),
            "anomalies": self._detect_anomalies(loop_a, loop_b, loop_c),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _calculate_rule_health(self) -> dict:
        total_rules = len(self._rule_injection_log)
        unique_rules = len(set(r for log in self._rule_injection_log for r in log.get("rule_ids", [])))
        return {
            "name": "Rule Loop",
            "metrics": {
                "rule_growth_rate": unique_rules,
                "rule_coverage": min(unique_rules / max(total_rules, 1), 1.0),
                "rule_conflict_rate": 0.0,
                "rule_obsolescence_rate": 0.0,
            },
            "health_score": 80,
        }

    def _calculate_knowledge_health(self) -> dict:
        return {
            "name": "Knowledge Loop",
            "metrics": {
                "auto_write_rate": self._knowledge_write_count,
                "error_propagation_depth": 0,
                "correction_rate": len(self._user_corrections),
                "consistency_score": 0.9,
            },
            "health_score": 75,
        }

    def _calculate_goal_health(self) -> dict:
        return {
            "name": "Goal Loop",
            "metrics": {
                "goal_completion_rate": self._goal_completion_count,
                "cascade_change_count": 0,
                "review_delay_count": 0,
            },
            "health_score": 70,
        }

    def _detect_anomalies(self, loop_a: dict, loop_b: dict, loop_c: dict) -> list[dict]:
        anomalies = []
        if loop_b["metrics"]["error_propagation_depth"] > 3:
            anomalies.append({"severity": "CRITICAL", "loop": "B", "message": "Error propagation > 3 layers"})
        if loop_a["metrics"]["rule_obsolescence_rate"] > 0.30:
            anomalies.append({"severity": "HIGH", "loop": "A", "message": "Rule obsolescence > 30%"})
        if loop_c["metrics"]["cascade_change_count"] > 50:
            anomalies.append({"severity": "HIGH", "loop": "C", "message": "Cascade changes > 50"})
        return anomalies

    def _write_observation(self, observation_type: str, data: dict):
        record = {
            "observation_id": f"obs-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "observation_point": observation_type,
            "data": data,
        }
        log_file = self.log_path / f"{observation_type}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_observations(self, observation_type: str, limit: int = 100) -> list[dict]:
        log_file = self.log_path / f"{observation_type}.jsonl"
        if not log_file.exists():
            return []
        observations = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    observations.append(json.loads(line))
        return observations[-limit:]
