import pytest
import tempfile
import os
from pathlib import Path
from storage.knowledge_indexer import KnowledgeIndexer
from storage.metadata_extractor import MetadataExtractor
from pipeline.call1_relevance import Call1Relevance

KB_PATH = Path(__file__).parent.parent / "knowledge-base"


@pytest.fixture
def call1():
    db_path = tempfile.mktemp(suffix=".sqlite")
    indexer = KnowledgeIndexer(db_path=db_path, knowledge_base_path=str(KB_PATH))
    extractor = MetadataExtractor()
    indexer.index_all(extractor)
    yield Call1Relevance(indexer=indexer)
    os.unlink(db_path)


class TestCall1Relevance:
    def test_returns_top_3_files(self, call1):
        email = "What is our current BTC allocation strategy?"
        result = call1.execute(email)
        assert len(result.top_files) <= 3

    def test_returns_routing_decision(self, call1):
        email = "What is our BTC position?"
        result = call1.execute(email)
        assert result.routing_decision in ["routine", "complex"]

    def test_complex_routing_for_regulatory(self, call1):
        email = "We need to discuss regulatory compliance for the new crypto fund with the SEC."
        result = call1.execute(email)
        assert result.routing_decision == "complex"

    def test_model_used(self, call1):
        result = call1.execute("Test email")
        assert result.model_used == "silra/glm-4.5"

    def test_token_usage_reported(self, call1):
        result = call1.execute("Test email")
        assert "input" in result.token_usage
        assert "output" in result.token_usage
