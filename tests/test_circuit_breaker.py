import pytest
from harness.intervener import Intervener
from harness.observer import Observer


class TestCircuitBreaker:
    @pytest.fixture
    def intervener(self):
        return Intervener()

    def test_circuit_opens_on_low_health(self, intervener):
        health_report = {"overall_health": 50, "anomalies": []}
        assert intervener.check_circuit_breaker(health_report) is True
        assert intervener.is_circuit_open() is True

    def test_circuit_stays_closed_on_healthy(self, intervener):
        health_report = {"overall_health": 80, "anomalies": []}
        assert intervener.check_circuit_breaker(health_report) is False
        assert intervener.is_circuit_open() is False

    def test_circuit_opens_on_critical_anomaly(self, intervener):
        health_report = {
            "overall_health": 75,
            "anomalies": [{"severity": "CRITICAL", "message": "Error propagation > 3 layers"}],
        }
        assert intervener.check_circuit_breaker(health_report) is True

    def test_circuit_reset(self, intervener):
        health_report = {"overall_health": 50, "anomalies": []}
        intervener.check_circuit_breaker(health_report)
        assert intervener.is_circuit_open() is True
        intervener.reset_circuit_breaker()
        assert intervener.is_circuit_open() is False

    def test_audit_queue_populated(self, intervener):
        intervener.add_to_audit_queue("req-001", "high", "knowledge_write", "Auto-write KB entry")
        queue = intervener.get_audit_queue()
        assert len(queue) >= 1

    def test_audit_approve(self, intervener):
        intervener.add_to_audit_queue("req-002", "high", "test", "Test action")
        assert intervener.approve_audit_item("req-002") is True
        pending = intervener.get_audit_queue("pending")
        assert not any(item["request_id"] == "req-002" for item in pending)

    def test_output_marker_high_confidence(self, intervener):
        marker = intervener.mark_output(confidence_score=0.9)
        assert marker.confidence_level == "high"

    def test_output_marker_low_confidence(self, intervener):
        marker = intervener.mark_output(confidence_score=0.3)
        assert marker.confidence_level == "low"

    def test_output_format_with_conflicts(self, intervener):
        marker = intervener.mark_output(
            confidence_score=0.7,
            conflicts=[{"metric": "BTC", "value_a": "8.2%", "value_b": "8.5%", "recommendation": "Verify"}],
        )
        formatted = intervener.format_output("Test content", marker)
        assert "Test content" in formatted
        assert "8.2%" in formatted
        assert "8.5%" in formatted

    def test_loop_break_report(self, intervener):
        report = intervener.get_loop_break_report()
        assert "circuit_breaker_open" in report
        assert "audit_queue_size" in report
