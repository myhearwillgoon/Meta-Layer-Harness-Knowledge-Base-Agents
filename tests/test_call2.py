import pytest
from pipeline.call2_embed import Call2Embed


class TestCall2Embed:
    @pytest.fixture
    def call2(self):
        return Call2Embed()

    def test_generates_2_queries(self, call2):
        email = "What is our BTC allocation and how does it compare to the risk framework?"
        result = call2.execute(email, ["btc-allocation-strategy.md", "risk-framework-2026.md"])
        assert len(result.queries) == 2

    def test_queries_are_natural_language(self, call2):
        email = "Update on ETH staking yields"
        result = call2.execute(email, ["eth-staking-position.md"])
        for q in result.queries:
            assert len(q.split()) > 2

    def test_model_used(self, call2):
        result = call2.execute("Test", [])
        assert result.model_used == "silra/glm-4.5"
