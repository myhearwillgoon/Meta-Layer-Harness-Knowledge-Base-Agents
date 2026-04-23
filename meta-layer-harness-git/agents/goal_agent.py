from typing import Optional
from storage.goal_store import GoalStore


class GoalAgent:
    def __init__(self, goal_store: GoalStore, observer=None):
        self.store = goal_store
        self.observer = observer

    def complete_leaf_goal(self, goal_id: str) -> dict:
        goal = self.store.get_goal(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        self.store.complete_goal(goal_id)
        completed = [goal_id]

        parent_id = goal.get("parent_id")
        while parent_id:
            parent = self.store.get_goal(parent_id)
            if not parent:
                break

            children = [self.store.get_goal(cid) for cid in parent.get("children_ids", [])]
            if all(c and c["status"] == "completed" for c in children):
                self.store.complete_goal(parent_id)
                completed.append(parent_id)
                parent_id = parent.get("parent_id")
            else:
                break

        if self.observer:
            for _ in completed:
                self.observer.record_goal_completion()

        return {"completed_goals": completed, "cascade_depth": len(completed)}

    def review_goal(self, goal_id: str) -> dict:
        goal = self.store.get_goal(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        review = {
            "goal_id": goal_id,
            "status": goal["status"],
            "stale": False,
            "overdue": False,
            "children_status": {},
        }

        for child in self.store.get_children(goal_id):
            review["children_status"][child["id"]] = child["status"]

        stale_goals = self.store.get_stale_goals()
        if goal in stale_goals:
            review["stale"] = True

        overdue_goals = self.store.get_overdue_goals()
        if goal in overdue_goals:
            review["overdue"] = True

        return review

    def review_all_goals(self) -> list[dict]:
        return [self.review_goal(g["id"]) for g in self.store.get_active_goals()]

    def create_goal(self, goal: dict) -> dict:
        if goal.get("parent_id"):
            parent = self.store.get_goal(goal["parent_id"])
            if not parent:
                raise ValueError(f"Parent goal {goal['parent_id']} not found")
        return self.store.create_goal(goal)

    def get_goal_tree(self, root_id: Optional[str] = None) -> dict:
        if root_id:
            root = self.store.get_goal(root_id)
            if not root:
                return {}
            return self._build_tree(root)

        roots = [g for g in self.store.get_all_goals() if not g.get("parent_id")]
        return {"roots": [self._build_tree(r) for r in roots]}

    def _build_tree(self, goal: dict) -> dict:
        children = self.store.get_children(goal["id"])
        return {
            "id": goal["id"],
            "title": goal["title"],
            "status": goal["status"],
            "autonomy_level": goal.get("autonomy_level", "observe"),
            "children": [self._build_tree(c) for c in children],
        }
