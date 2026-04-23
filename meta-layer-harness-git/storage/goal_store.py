import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


class GoalStore:
    def __init__(self, goals_path: str):
        self.goals_path = Path(goals_path)
        self._ensure_file()

    def _ensure_file(self):
        if not self.goals_path.exists():
            self.goals_path.write_text(json.dumps({"version": "1.0.0", "goals": [], "metadata": {}}, indent=2))

    def _load(self) -> dict:
        return json.loads(self.goals_path.read_text(encoding="utf-8"))

    def _save(self, data: dict):
        data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.goals_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def get_goal(self, goal_id: str) -> Optional[dict]:
        data = self._load()
        for g in data["goals"]:
            if g["id"] == goal_id:
                return g
        return None

    def get_all_goals(self) -> list[dict]:
        return self._load()["goals"]

    def get_active_goals(self) -> list[dict]:
        return [g for g in self._load()["goals"] if g["status"] == "active"]

    def get_leaf_goals(self) -> list[dict]:
        return [g for g in self._load()["goals"] if not g.get("children_ids")]

    def create_goal(self, goal: dict) -> dict:
        if goal.get("parent_id"):
            parent = self.get_goal(goal["parent_id"])
            if not parent:
                raise ValueError(f"Parent goal {goal['parent_id']} not found")
            if goal["id"] not in parent.get("children_ids", []):
                parent["children_ids"].append(goal["id"])
                self._save(self._load())

        goal.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        goal.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
        goal.setdefault("status", "active")
        goal.setdefault("children_ids", [])

        data = self._load()
        data["goals"].append(goal)
        self._save(data)
        return goal

    def update_goal(self, goal_id: str, updates: dict) -> Optional[dict]:
        data = self._load()
        for g in data["goals"]:
            if g["id"] == goal_id:
                g.update(updates)
                g["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save(data)
                return g
        return None

    def complete_goal(self, goal_id: str) -> Optional[dict]:
        return self.update_goal(goal_id, {"status": "completed"})

    def delete_goal(self, goal_id: str) -> bool:
        data = self._load()
        original_len = len(data["goals"])
        data["goals"] = [g for g in data["goals"] if g["id"] != goal_id]
        if len(data["goals"]) < original_len:
            for g in data["goals"]:
                if goal_id in g.get("children_ids", []):
                    g["children_ids"].remove(goal_id)
            self._save(data)
            return True
        return False

    def get_children(self, goal_id: str) -> list[dict]:
        goal = self.get_goal(goal_id)
        if not goal:
            return []
        return [self.get_goal(cid) for cid in goal.get("children_ids", []) if self.get_goal(cid)]

    def get_overdue_goals(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        overdue = []
        for g in self._load()["goals"]:
            if g["status"] == "active" and g.get("deadline"):
                deadline = datetime.fromisoformat(g["deadline"])
                if deadline < now:
                    overdue.append(g)
        return overdue

    def get_stale_goals(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        stale = []
        for g in self._load()["goals"]:
            stale_days = g.get("stale_after_days", 30)
            updated = datetime.fromisoformat(g.get("updated_at", g.get("created_at", "")))
            if (now - updated).days > stale_days:
                stale.append(g)
        return stale
