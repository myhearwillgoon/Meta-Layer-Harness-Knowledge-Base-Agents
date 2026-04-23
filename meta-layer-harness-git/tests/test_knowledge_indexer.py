import pytest
import tempfile
import os
from pathlib import Path
from storage.knowledge_indexer import KnowledgeIndexer
from storage.metadata_extractor import MetadataExtractor
from storage.wiki_link_parser import WikiLinkParser

KB_PATH = Path(__file__).parent.parent / "knowledge-base"


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def indexer(temp_db):
    return KnowledgeIndexer(db_path=temp_db, knowledge_base_path=str(KB_PATH))


@pytest.fixture
def extractor():
    return MetadataExtractor()


@pytest.fixture
def wiki_parser(temp_db):
    return WikiLinkParser(db_path=temp_db)


class TestKnowledgeIndexer:
    def test_index_all_files(self, indexer, extractor):
        count = indexer.index_all(extractor)
        assert count == 77

    def test_index_single_file(self, indexer, extractor):
        test_file = KB_PATH / "decisions" / "investment-committee-2026-03-15.md"
        if test_file.exists():
            record = indexer.index_file(test_file, extractor)
            assert record["file_path"] is not None
            assert record["authority_score"] == 5

    def test_get_by_path(self, indexer, extractor):
        indexer.index_all(extractor)
        result = indexer.get_by_path("decisions/investment-committee-2026-03-15.md")
        assert result is not None
        assert result["authority_score"] == 5

    def test_search_by_type(self, indexer, extractor):
        indexer.index_all(extractor)
        results = indexer.search_by_type("decision")
        assert len(results) > 0

    def test_get_top_by_authority(self, indexer, extractor):
        indexer.index_all(extractor)
        top = indexer.get_top_by_authority(5)
        assert len(top) <= 5
        assert all(r["authority_score"] >= top[-1]["authority_score"] for r in top)

    def test_get_all_file_names(self, indexer, extractor):
        indexer.index_all(extractor)
        names = indexer.get_all_file_names()
        assert len(names) == 77

    def test_get_stats(self, indexer, extractor):
        indexer.index_all(extractor)
        stats = indexer.get_stats()
        assert stats["total_files"] == 77
        assert stats["avg_authority"] > 0
        assert stats["avg_freshness"] > 0

    def test_mark_conflict(self, indexer, extractor):
        indexer.index_all(extractor)
        indexer.mark_conflict("decisions/investment-committee-2026-03-15.md", "BTC 8.2% vs 8.5%")
        conflicts = indexer.get_conflicting_entries()
        assert len(conflicts) >= 1


class TestMetadataExtractor:
    def test_authority_investment_committee(self, extractor):
        from pathlib import Path
        score = extractor._compute_authority(Path("investment-committee-2026-03-15.md"))
        assert score == 5

    def test_authority_risk_committee(self, extractor):
        score = extractor._compute_authority(Path("risk-committee-2026-03-10.md"))
        assert score == 5

    def test_authority_weekly_digest(self, extractor):
        score = extractor._compute_authority(Path("weekly-digest-2026-03-24.md"))
        assert score == 3

    def test_authority_rumor(self, extractor):
        score = extractor._compute_authority(Path("rumor-coinbase-acquisition.md"))
        assert score == 1

    def test_freshness_recent(self, extractor):
        score = extractor._compute_freshness(Path("weekly-digest-2026-03-24.md"))
        assert 1 <= score <= 5

    def test_wiki_link_count(self, extractor):
        content = "See [[btc-allocation-strategy]] and [[alex-chen]]"
        count = extractor._count_wiki_links(content)
        assert count == 2


class TestWikiLinkParser:
    def test_parse_content(self, wiki_parser):
        content = "Refer to [[btc-allocation-strategy]] and [[alex-chen]] for details."
        links = wiki_parser.parse_content(content)
        assert len(links) == 2
        assert links[0]["target"] == "btc-allocation-strategy"

    def test_parse_file(self, wiki_parser):
        content = "See [[alex-chen]] and [[nonexistent-file]]"
        valid_files = {"alex-chen.md", "btc-allocation-strategy.md"}
        from pathlib import Path
        links = wiki_parser.parse_file(Path("test.md"), content, valid_files)
        assert len(links) == 2
        assert links[0]["is_broken"] == 0
        assert links[1]["is_broken"] == 1

    def test_get_backlinks(self, wiki_parser):
        content = "See [[target-file]]"
        valid_files = {"target-file.md"}
        from pathlib import Path
        wiki_parser.parse_file(Path("source-a.md"), content, valid_files)
        wiki_parser.parse_file(Path("source-b.md"), content, valid_files)
        backlinks = wiki_parser.get_backlinks("target-file")
        assert len(backlinks) >= 2

    def test_expand_with_backlinks(self, wiki_parser):
        valid_files = {"a.md", "b.md", "c.md"}
        from pathlib import Path
        wiki_parser.parse_file(Path("a.md"), "See [[b]]", valid_files)
        wiki_parser.parse_file(Path("b.md"), "See [[c]]", valid_files)
        expanded = wiki_parser.expand_with_backlinks(["a.md"], valid_files)
        assert "a.md" in expanded
        assert "b.md" in expanded

    def test_link_graph_stats(self, wiki_parser):
        stats = wiki_parser.get_link_graph_stats()
        assert "total_links" in stats
        assert "broken_links" in stats
