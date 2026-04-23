import sqlite3
import json
import struct
import os
from pathlib import Path
from typing import Optional


class VectorStore:
    def __init__(self, db_path: str, api_client=None):
        self.db_path = db_path
        self.api_client = api_client
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vector_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    embedding BLOB NOT NULL,
                    content_preview TEXT,
                    source_type TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_path, chunk_index)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vector_file ON vector_index(file_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vector_type ON vector_index(source_type)")

    def store_embedding(self, file_path: str, chunk_index: int, embedding: list[float], content_preview: str = "", source_type: str = ""):
        emb_bytes = struct.pack(f"{len(embedding)}f", *embedding)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO vector_index
                   (file_path, chunk_index, embedding, content_preview, source_type)
                   VALUES (?, ?, ?, ?, ?)""",
                (file_path, chunk_index, emb_bytes, content_preview, source_type),
            )

    def search(self, query_embedding: list[float], limit: int = 30) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT file_path, chunk_index, embedding, content_preview, source_type FROM vector_index").fetchall()

        results = []
        for file_path, chunk_idx, emb_bytes, preview, stype in rows:
            stored = struct.unpack(f"{len(query_embedding)}f", emb_bytes)
            similarity = self._cosine_similarity(query_embedding, stored)
            results.append({
                "file_path": file_path,
                "chunk_index": chunk_idx,
                "similarity": similarity,
                "content_preview": preview,
                "source_type": stype,
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def search_multi(self, query_embeddings: list[list[float]], limit_per_query: int = 30) -> list[dict]:
        all_results = []
        for emb in query_embeddings:
            all_results.extend(self.search(emb, limit_per_query))
        seen = set()
        deduped = []
        for r in all_results:
            key = (r["file_path"], r["chunk_index"])
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return sorted(deduped, key=lambda x: x["similarity"], reverse=True)

    def get_embedding_count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM vector_index").fetchone()[0]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
