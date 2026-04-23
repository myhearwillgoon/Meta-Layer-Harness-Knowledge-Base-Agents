import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


class DecisionLog:
    def __init__(self, log_path: str = "logs/decisions/"):
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self._log_file = self.log_path / "decisions.jsonl"

    def log_decision(self, request_id: str, data: dict):
        record = {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def query_by_request_id(self, request_id: str) -> Optional[dict]:
        if not self._log_file.exists():
            return None
        with open(self._log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if record.get("request_id") == request_id:
                        return record
        return None

    def query_by_rule(self, rule_id: str, date_range: Optional[tuple[str, str]] = None) -> list[dict]:
        results = []
        if not self._log_file.exists():
            return results
        with open(self._log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    rules = record.get("rules_injected", [])
                    if rule_id in rules:
                        if date_range:
                            ts = record.get("timestamp", "")
                            if date_range[0] <= ts <= date_range[1]:
                                results.append(record)
                        else:
                            results.append(record)
        return results

    def visualize_prompt_contribution(self, request_id: str) -> Optional[dict]:
        record = self.query_by_request_id(request_id)
        if not record:
            return None
        prompt_assembly = record.get("prompt_assembly", {})
        sources = prompt_assembly.get("sources", [])
        return {
            "request_id": request_id,
            "sources": [
                {"id": s.get("id", ""), "relevance": s.get("relevance", 0), "contribution": s.get("contribution", "")}
                for s in sources
            ],
        }

    def get_all(self, limit: int = 100) -> list[dict]:
        results = []
        if not self._log_file.exists():
            return results
        with open(self._log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
        return results[-limit:]

    def get_stats(self) -> dict:
        if not self._log_file.exists():
            return {"total": 0}
        count = 0
        with open(self._log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return {"total": count}
