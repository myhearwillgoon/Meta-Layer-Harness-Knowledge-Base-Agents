import difflib
from datetime import datetime, timezone
from typing import Optional


class ReplyAgent:
    def __init__(self, observer=None, rule_injector=None):
        self.observer = observer
        self.rule_injector = rule_injector
        self._drafts = {}

    def generate_draft(self, analysis: str, email_content: str, style: str = "professional") -> dict:
        draft_id = f"draft-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        draft = {
            "id": draft_id,
            "content": f"[DRAFT] Based on analysis: {analysis[:200]}...",
            "style": style,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._drafts[draft_id] = draft
        return draft

    def capture_user_correction(self, draft_id: str, user_edit: str) -> dict:
        original = self._drafts.get(draft_id)
        if not original:
            raise ValueError(f"Draft {draft_id} not found")

        diff = self._compute_diff(original["content"], user_edit)

        if self.observer:
            self.observer.record_user_correction(
                draft_id=draft_id,
                original=original["content"],
                user_edit=user_edit,
                diff=diff,
            )

        lesson = self._generate_lesson(diff)

        self._drafts[draft_id]["final_content"] = user_edit
        self._drafts[draft_id]["corrected_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "draft_id": draft_id,
            "lesson": lesson,
            "diff_summary": diff,
        }

    def get_draft(self, draft_id: str) -> Optional[dict]:
        return self._drafts.get(draft_id)

    def _compute_diff(self, original: str, edited: str) -> list[dict]:
        diff = list(difflib.unified_diff(
            original.splitlines(),
            edited.splitlines(),
            lineterm="",
        ))
        changes = []
        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                changes.append({"type": "added", "content": line[1:]})
            elif line.startswith("-") and not line.startswith("---"):
                changes.append({"type": "removed", "content": line[1:]})
        return changes

    def _generate_lesson(self, diff: list[dict]) -> str:
        if not diff:
            return "No corrections made"
        additions = [d["content"] for d in diff if d["type"] == "added"]
        removals = [d["content"] for d in diff if d["type"] == "removed"]
        lesson = "User corrections: "
        if removals:
            lesson += f"Removed: {', '.join(removals[:3])}. "
        if additions:
            lesson += f"Added: {', '.join(additions[:3])}."
        return lesson
