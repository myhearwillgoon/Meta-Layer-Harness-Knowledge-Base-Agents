import os
from pathlib import Path
from datetime import datetime, timezone
from storage.knowledge_indexer import KnowledgeIndexer
from storage.wiki_link_parser import WikiLinkParser
from storage.metadata_extractor import MetadataExtractor


class KnowledgeAgent:
    def __init__(self, indexer: KnowledgeIndexer, wiki_parser: WikiLinkParser,
                 extractor: MetadataExtractor, knowledge_base_path: str, observer=None):
        self.indexer = indexer
        self.wiki_parser = wiki_parser
        self.extractor = extractor
        self.kb_path = Path(knowledge_base_path)
        self.observer = observer

    def append_entry(self, title: str, content: str, category: str = "decisions") -> dict:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"{title.lower().replace(' ', '-')}-{timestamp}.md"
        file_path = self.kb_path / category / filename

        file_path.write_text(content, encoding="utf-8")

        self.indexer.index_file(file_path, self.extractor)

        wiki_links = self.wiki_parser.parse_content(content)
        valid_files = set(self.indexer.get_all_file_names())
        self.wiki_parser.parse_file(file_path, content, valid_files)

        if self.observer:
            meta = self.extractor.extract(file_path, content)
            self.observer.record_knowledge_metadata(str(file_path), meta)
            self.observer.record_knowledge_write()

        return {"success": True, "file_path": str(file_path), "title": title}

    def create_entry(self, title: str, content: str, category: str = "decisions") -> dict:
        if not self._request_approval("create", title):
            return {"success": False, "reason": "Approval not granted"}
        return self.append_entry(title, content, category)

    def rename_entry(self, old_path: str, new_title: str) -> dict:
        if not self._request_approval("rename", old_path):
            return {"success": False, "reason": "Approval not granted"}
        old_file = Path(old_path)
        new_file = old_file.parent / f"{new_title.lower().replace(' ', '-')}.md"
        old_file.rename(new_file)
        self.indexer.index_file(new_file, self.extractor)
        return {"success": True, "new_path": str(new_file)}

    def get_entry(self, file_path: str) -> dict:
        record = self.indexer.get_by_path(file_path)
        if not record:
            return {}
        full_path = self.kb_path / file_path
        if full_path.exists():
            record["content"] = full_path.read_text(encoding="utf-8")
        return record

    def search_entries(self, query: str) -> list[dict]:
        all_files = self.indexer.get_all_file_names()
        query_lower = query.lower()
        matches = []
        for f in all_files:
            if query_lower in f.lower():
                record = self.indexer.get_by_path(f)
                if record:
                    matches.append(record)
        return sorted(matches, key=lambda x: x.get("authority_score", 0), reverse=True)

    def _request_approval(self, operation: str, target: str) -> bool:
        return os.getenv("AUTO_APPROVE_KB", "false").lower() == "true"
