import time
import os
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class TickResult:
    tick_number: int
    events_found: int
    tasks_dispatched: int
    cost_usd: float
    latency_ms: float
    timestamp: str

    def to_dict(self):
        return asdict(self)


class Daemon:
    def __init__(self, agents: dict, goal_agent=None, observer=None, api_client=None):
        self.agents = agents
        self.goal_agent = goal_agent
        self.observer = observer
        self.api_client = api_client
        self.tick_interval = int(os.getenv("DAEMON_TICK_INTERVAL_MINUTES", "5")) * 60
        self.tick_count = 0
        self._running = False
        self._event_log = []

    def tick(self) -> TickResult:
        start = time.time()
        self.tick_count += 1

        events = self._gather_events()

        if not events:
            latency = (time.time() - start) * 1000
            return TickResult(
                tick_number=self.tick_count,
                events_found=0,
                tasks_dispatched=0,
                cost_usd=0.0,
                latency_ms=latency,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        goals = self._load_goals() if self.goal_agent else []

        triage_result = self._triage(events, goals)

        dispatched = self._dispatch(triage_result)

        latency = (time.time() - start) * 1000

        if self.observer:
            self.observer.record_loop_health({
                "tick": self.tick_count,
                "events": len(events),
                "dispatched": dispatched,
                "latency_ms": latency,
            })

        return TickResult(
            tick_number=self.tick_count,
            events_found=len(events),
            tasks_dispatched=dispatched,
            cost_usd=triage_result.get("cost", 0.0),
            latency_ms=latency,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def run_loop(self, max_ticks: Optional[int] = None):
        self._running = True
        ticks = 0
        while self._running:
            result = self.tick()
            ticks += 1
            if max_ticks and ticks >= max_ticks:
                break
            time.sleep(self.tick_interval)

    def stop(self):
        self._running = False

    def _gather_events(self) -> list[dict]:
        events = list(self._event_log)
        self._event_log.clear()
        return events

    def add_event(self, event: dict):
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._event_log.append(event)

    def _load_goals(self) -> list[dict]:
        if self.goal_agent:
            return self.goal_agent.store.get_active_goals()
        return []

    def _triage(self, events: list[dict], goals: list[dict]) -> dict:
        triaged = []
        for event in events:
            agent_type = self._classify_event(event)
            triaged.append({
                "event": event,
                "target_agent": agent_type,
                "priority": event.get("priority", "normal"),
            })
        return {"triaged": triaged, "cost": 0.0}

    def _classify_event(self, event: dict) -> str:
        event_type = event.get("type", "")
        if "email" in event_type:
            return "email_agent"
        elif "knowledge" in event_type:
            return "knowledge_agent"
        elif "goal" in event_type:
            return "goal_agent"
        elif "reply" in event_type:
            return "reply_agent"
        return "email_agent"

    def _dispatch(self, triage_result: dict) -> int:
        dispatched = 0
        for item in triage_result.get("triaged", []):
            agent_name = item["target_agent"]
            agent = self.agents.get(agent_name)
            if agent and hasattr(agent, "process_email"):
                event = item["event"]
                if "content" in event:
                    agent.process_email(event["content"])
                    dispatched += 1
            elif agent:
                dispatched += 1
        return dispatched
