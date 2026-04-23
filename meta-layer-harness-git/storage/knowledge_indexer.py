import sqlite3
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class KnowledgeIndexer:
    def __init__(self, db_path: str, knowledge_base_path: str):
        self.db_path = db_path
        self.knowledge_base_path = Path(knowledge_base_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_index (
                    file_path TEXT PRIMARY KEY,
                    title TEXT,
                    modified_at TEXT,
                    authority_score INTEGER DEFAULT 3,
                    freshness_score INTEGER DEFAULT 3,
                    source_type TEXT,
                    content_hash TEXT,
                    entity_count INTEGER DEFAULT 0,
                    wiki_link_count INTEGER DEFAULT 0,
                    conflict_flag INTEGER DEFAULT 0,
                    conflict_details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_authority
                ON knowledge_index(authority_score DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_freshness
                ON knowledge_index(freshness_score DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_type
                ON knowledge_index(source_type)
            """)

    def index_all(self, metadata_extractor=None) -> int:
        indexed = 0
        for md_file in self.knowledge_base_path.rglob("*.md"):
            try:
                self.index_file(md_file, metadata_extractor)
                indexed += 1
            except Exception as e:
                print(f"[WARN] Skipping {md_file}: {e}")
        return indexed

    def index_file(self, file_path: Path, metadata_extractor=None) -> dict:
        stat = file_path.stat()
        content = file_path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        record = {
            "file_path": str(file_path.relative_to(self.knowledge_base_path)),
            "title": file_path.stem.replace("-", " ").title(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "content_hash": content_hash,
        }

        if metadata_extractor:
            meta = metadata_extractor.extract(file_path, content)
            record.update(meta)

        with sqlite3.connect(self.db_path) as conn:
            columns = ", ".join(record.keys())
            placeholders = ", ".join([f":{k}" for k in record.keys()])
            conn.execute(
                f"""INSERT OR REPLACE INTO knowledge_index
                    ({columns}, updated_at)
                    VALUES ({placeholders}, CURRENT_TIMESTAMP)""",
                record,
            )

        return record

    def get_by_path(self, file_path: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM knowledge_index WHERE file_path = ?",
                (file_path,),
            ).fetchone()
            return dict(row) if row else None

    def search_by_type(self, source_type: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM knowledge_index WHERE source_type = ? ORDER BY authority_score DESC",
                (source_type,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_top_by_authority(self, limit: int = 10) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM knowledge_index ORDER BY authority_score DESC, freshness_score DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_file_names(self) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT file_path FROM knowledge_index").fetchall()
            return [r[0] for r in rows]

    def mark_conflict(self, file_path: str, conflict_details: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE knowledge_index
                   SET conflict_flag = 1, conflict_details = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE file_path = ?""",
                (conflict_details, file_path),
            )

    def get_conflicting_entries(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM knowledge_index WHERE conflict_flag = 1"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(authority_score) as avg_authority,
                    AVG(freshness_score) as avg_freshness,
                    SUM(conflict_flag) as conflicts
                FROM knowledge_index
            """).fetchone()
            return {
                "total_files": row[0],
                "avg_authority": round(row[1], 2) if row[1] else 0,
                "avg_freshness": round(row[2], 2) if row[2] else 0,
                "conflicts": row[3] or 0,
            }
