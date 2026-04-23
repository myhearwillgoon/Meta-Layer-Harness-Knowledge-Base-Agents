import pytest
from harness.evaluator import Evaluator


class TestConflictDetection:
    @pytest.fixture
    def evaluator(self):
        return Evaluator(numerical_threshold=0.03)

    def test_numerical_conflict_btc(self, evaluator):
        source_a = {"source": "investment-committee-2026-03-15", "value": "8.2%", "authority_score": 5}
        source_b = {"source": "weekly-digest-2026-03-24", "value": "8.5%", "authority_score": 3}
        conflict = evaluator.detect_numerical_conflict(source_a, source_b, "BTC_仓位")
        assert conflict is not None
        assert conflict.conflict_type == "numerical"
        assert conflict.metric == "BTC_仓位"

    def test_numerical_conflict_crypto_total(self, evaluator):
        source_a = {"source": "investment-committee", "value": "15.0%", "authority_score": 5}
        source_b = {"source": "weekly-digest", "value": "15.7%", "authority_score": 3}
        conflict = evaluator.detect_numerical_conflict(source_a, source_b, "加密总仓位")
        assert conflict is not None

    def test_no_conflict_within_threshold(self, evaluator):
        source_a = {"source": "a", "value": "10.0%", "authority_score": 3}
        source_b = {"source": "b", "value": "10.1%", "authority_score": 3}
        conflict = evaluator.detect_numerical_conflict(source_a, source_b, "test")
        assert conflict is None

    def test_semantic_conflict(self, evaluator):
        conflict = evaluator.detect_semantic_conflict(
            "We are bullish on BTC this quarter",
            "We are bearish on BTC this quarter"
        )
        assert conflict is not None
        assert conflict.conflict_type == "semantic"

    def test_no_semantic_conflict(self, evaluator):
        conflict = evaluator.detect_semantic_conflict(
            "BTC allocation is 8.2%",
            "ETH allocation is 5.0%"
        )
        assert conflict is None

    def test_authority_conflict(self, evaluator):
        source_a = {"source": "投委会", "authority_score": 5}
        source_b = {"source": "个人笔记", "authority_score": 2}
        conflict = evaluator.detect_authority_conflict(source_a, source_b)
        assert conflict is not None
        assert conflict.conflict_type == "authority"

    def test_temporal_conflict(self, evaluator):
        event_a = {"date": "2026-03-24", "supersedes": False}
        event_b = {"date": "2026-03-15", "supersedes": False}
        conflict = evaluator.detect_temporal_conflict(event_a, event_b)
        assert conflict is not None

    def test_confidence_calculation_fact_query(self, evaluator):
        confidence = evaluator.calculate_confidence(
            authority=5, freshness=4, consistency=0.9, query_type="fact_query"
        )
        assert 0 <= confidence <= 1

    def test_confidence_calculation_decision_rationale(self, evaluator):
        confidence = evaluator.calculate_confidence(
            authority=5, freshness=2, consistency=0.8, query_type="decision_rationale"
        )
        assert 0 <= confidence <= 1

    def test_confidence_calculation_compliance_check(self, evaluator):
        confidence = evaluator.calculate_confidence(
            authority=4, freshness=4, consistency=0.9, query_type="compliance_check"
        )
        assert 0 <= confidence <= 1
