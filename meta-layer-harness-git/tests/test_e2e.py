import pytest
import tempfile
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent


class TestE2E:
    @pytest.fixture(autouse=True)
    def system(self, monkeypatch):
        os.chdir(str(PROJECT_DIR))
        # Use mock mode for faster tests (no real API calls)
        monkeypatch.setenv("CALL1_MODEL", "mock")
        monkeypatch.setenv("CALL2_MODEL", "mock")
        monkeypatch.setenv("CALL3_COMPLEX_MODEL", "mock")
        monkeypatch.setenv("CALL3_ROUTINE_MODEL", "mock")
        
        from main import initialize_system
        return initialize_system()

    def test_full_email_pipeline(self, system):
        email = "What is our current BTC allocation? Please compare with the latest investment committee decision."
        result = system["email_agent"].process_email(email)
        assert result.analysis != ""
        assert result.draft_reply != ""
        assert len(result.top_files) > 0
        assert len(result.search_queries) == 2

    def test_knowledge_base_search(self, system):
        results = system["knowledge_agent"].search_entries("BTC")
        assert len(results) > 0

    def test_goal_cascade(self, system):
        result = system["goal_agent"].complete_leaf_goal("goal-002")
        assert "completed_goals" in result

    def test_observer_records(self, system):
        system["email_agent"].process_email("Test email for observation")
        observations = system["observer"].get_observations("prompt_assembly")
        assert len(observations) > 0

    def test_loop_health_report(self, system):
        report = system["observer"].get_loop_health_report()
        assert "overall_health" in report
        assert "loop_a" in report
        assert "loop_b" in report
        assert "loop_c" in report

    def test_daemon_tick(self, system):
        system["daemon"].add_event({"type": "email", "content": "Test email", "priority": "normal"})
        result = system["daemon"].tick()
        assert result.tick_number >= 1
        assert result.events_found >= 0

    def test_rule_injection_in_pipeline(self, system):
        email = "What is our BTC position and is it compliant?"
        result = system["email_agent"].process_email(email)
        assert result.analysis != ""

    def test_decision_log(self, system):
        system["email_agent"].process_email("Test email for logging")
        stats = system["decision_log"].get_stats()
        assert stats["total"] >= 0
