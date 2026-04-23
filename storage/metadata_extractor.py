import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


AUTHORITY_MAP = {
    "investment-committee": 5,
    "risk-committee": 5,
    "board": 5,
    "risk-framework": 4,
    "compliance": 4,
    "policy": 4,
    "employee-trading": 4,
    "aml-kyc": 4,
    "weekly-digest": 3,
    "research-memo": 3,
    "budget": 3,
    "stress-test": 3,
    "informal": 2,
    "slack-discussion": 2,
    "rumor": 1,
}

SOURCE_TYPE_MAP = {
    "people/": "people",
    "projects/": "project",
    "decisions/": "decision",
    "vendors/": "vendor",
    "policies/": "policy",
}


class MetadataExtractor:
    def extract(self, file_path: Path, content: str) -> dict:
        return {
            "title": self._extract_title(file_path, content),
            "authority_score": self._compute_authority(file_path),
            "freshness_score": self._compute_freshness(file_path),
            "source_type": self._detect_source_type(file_path),
            "entity_count": self._count_entities(content),
            "wiki_link_count": self._count_wiki_links(content),
        }

    def _extract_title(self, file_path: Path, content: str) -> str:
        match = re.match(r"^#\s+(.+)", content.strip())
        if match:
            return match.group(1).strip()
        return file_path.stem.replace("-", " ").title()

    def _compute_authority(self, file_path: Path) -> int:
        name = file_path.stem.lower()
        for keyword, score in AUTHORITY_MAP.items():
            if keyword in name:
                return score
        return 3

    def _compute_freshness(self, file_path: Path) -> int:
        name = file_path.stem.lower()
        date_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", name)
        if date_match:
            try:
                file_date = datetime(
                    int(date_match.group(1)),
                    int(date_match.group(2)),
                    int(date_match.group(3)),
                    tzinfo=timezone.utc,
                )
                now = datetime.now(timezone.utc)
                days_old = (now - file_date).days
                if days_old < 1:
                    return 5
                elif days_old < 7:
                    return 4
                elif days_old < 30:
                    return 3
                elif days_old < 90:
                    return 2
                else:
                    return 1
            except (ValueError, OverflowError):
                pass
        return 3

    def _detect_source_type(self, file_path: Path) -> str:
        rel = str(file_path)
        for prefix, stype in SOURCE_TYPE_MAP.items():
            if prefix in rel:
                return stype
        return "general"

    def _count_entities(self, content: str) -> int:
        entities = set()
        for match in re.finditer(r"\b[A-Z]{2,5}\b", content):
            word = match.group(0)
            if word not in {"The", "And", "For", "Not", "But", "All", "Each"}:
                entities.add(word)
        return len(entities)

    def _count_wiki_links(self, content: str) -> int:
        return len(re.findall(r"\[\[([^\]]+)\]\]", content))
