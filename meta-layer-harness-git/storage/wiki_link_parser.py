import re
import sqlite3
from pathlib import Path
from typing import Optional


class WikiLinkParser:
    MAX_LINKS_PER_NOTE = 30

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wiki_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file TEXT NOT NULL,
                    target_file TEXT NOT NULL,
                    link_text TEXT,
                    is_broken INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_file, target_file)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wiki_source
                ON wiki_links(source_file)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wiki_target
                ON wiki_links(target_file)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backlinks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_file TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(target_file, source_file)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_backlink_target
                ON backlinks(target_file)
            """)

    def parse_content(self, content: str) -> list[dict]:
        pattern = r"\[\[([^\]]+)\]\]"
        links = []
        for match in re.finditer(pattern, content):
            raw = match.group(1).strip()
            parts = raw.split("|")
            target = parts[0].strip()
            display = parts[1].strip() if len(parts) > 1 else target
            links.append({"target": target, "display": display})
        return links[: self.MAX_LINKS_PER_NOTE]

    def parse_file(self, file_path: Path, content: str, valid_files: set[str]) -> list[dict]:
        links = self.parse_content(content)
        source = str(file_path.stem)
        results = []

        with sqlite3.connect(self.db_path) as conn:
            for link in links:
                target = link["target"]
                is_broken = 0

                target_path = target + ".md" if not target.endswith(".md") else target
                if target_path not in valid_files:
                    is_broken = 1

                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO wiki_links
                           (source_file, target_file, link_text, is_broken)
                           VALUES (?, ?, ?, ?)""",
                        (source, target, link["display"], is_broken),
                    )
                    if not is_broken:
                        conn.execute(
                            """INSERT OR IGNORE INTO backlinks
                               (target_file, source_file)
                               VALUES (?, ?)""",
                            (target, source),
                        )
                except sqlite3.IntegrityError:
                    pass

                results.append({**link, "is_broken": is_broken})

        return results

    def get_backlinks(self, target_file: str, limit: int = 30) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT source_file FROM backlinks WHERE target_file = ? LIMIT ?",
                (target_file, limit),
            ).fetchall()
            return [r[0] for r in rows]

    def get_outbound_links(self, source_file: str, limit: int = 30) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT target_file, link_text, is_broken FROM wiki_links WHERE source_file = ? LIMIT ?",
                (source_file, limit),
            ).fetchall()
            return [{"target": r[0], "text": r[1], "broken": bool(r[2])} for r in rows]

    def expand_with_backlinks(self, seed_files: list[str], valid_files: set[str], max_links: int = 30) -> set[str]:
        expanded = set(seed_files)
        for f in seed_files:
            stem = Path(f).stem if isinstance(f, str) else f.stem
            outbound = self.get_outbound_links(stem, limit=max_links)
            for link in outbound:
                if not link["broken"]:
                    target = link["target"]
                    if not target.endswith(".md"):
                        target = target + ".md"
                    if target in valid_files:
                        expanded.add(target)
            backlinks = self.get_backlinks(stem, limit=max_links)
            for bl in backlinks:
                if not bl.endswith(".md"):
                    bl = bl + ".md"
                if bl in valid_files:
                    expanded.add(bl)
        return expanded

    def get_broken_links(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT source_file, target_file, link_text FROM wiki_links WHERE is_broken = 1"
            ).fetchall()
            return [{"source": r[0], "target": r[1], "text": r[2]} for r in rows]

    def get_link_graph_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM wiki_links").fetchone()[0]
            broken = conn.execute("SELECT COUNT(*) FROM wiki_links WHERE is_broken = 1").fetchone()[0]
            backlinks = conn.execute("SELECT COUNT(*) FROM backlinks").fetchone()[0]
            return {"total_links": total, "broken_links": broken, "backlinks": backlinks}
