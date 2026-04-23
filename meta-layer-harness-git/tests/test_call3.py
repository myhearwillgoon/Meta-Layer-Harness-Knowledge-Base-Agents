import pytest
from pipeline.call3_analysis import Call3Analysis


class TestCall3Analysis:
    @pytest.fixture
    def call3(self):
        return Call3Analysis()

    def test_routine_analysis(self, call3):
        email = "Quick update on portfolio performance"
        context = ["weekly-digest-2026-03-24.md"]
        result = call3.execute(email, context, is_complex=False)
        assert result.analysis != ""
        assert result.model_used == "glm-4.5-air"

    def test_complex_analysis(self, call3):
        email = "Regulatory compliance review for new crypto fund"
        context = ["risk-framework-2026.md", "compliance-crypto-guidelines.md"]
        result = call3.execute(email, context, is_complex=True)
        assert result.analysis != ""
        assert result.model_used == "glm-4.5-air"

    def test_output_structure(self, call3):
        result = call3.execute("Test", ["context.md"])
        assert hasattr(result, "analysis")
        assert hasattr(result, "draft_reply")
        assert hasattr(result, "knowledge_updates")
        assert hasattr(result, "fact_check")
        assert hasattr(result, "model_used")
        assert hasattr(result, "confidence")
        assert hasattr(result, "token_usage")
