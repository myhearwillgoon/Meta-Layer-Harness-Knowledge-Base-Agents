# User Guide

## Quick Start

```bash
cd meta-layer-harness
pip install -r requirements.txt
python main.py
```

## Processing Emails

```python
from main import initialize_system
system = initialize_system()
result = system["email_agent"].process_email("Your email content here")
print(result.analysis)
print(result.draft_reply)
```

## Knowledge Base Management

```python
# Search
results = system["knowledge_agent"].search_entries("BTC")

# Append entry (auto-approved)
system["knowledge_agent"].append_entry("Meeting Notes", "# Content", "decisions")

# Create entry (requires approval)
system["knowledge_agent"].create_entry("New Policy", "# Content", "policies")
```

## Goal Management

```python
# Complete a leaf goal (cascades to parent)
result = system["goal_agent"].complete_leaf_goal("goal-002")

# Review all goals
reviews = system["goal_agent"].review_all_goals()

# View goal tree
tree = system["goal_agent"].get_goal_tree()
```

## HITL Web UI

```bash
python main.py webui
# Open http://localhost:8080
# View audit queue, approve/reject actions
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `python main.py tick` | Run one daemon tick |
| `python main.py health` | Get loop health report |
| `python main.py stats` | Get system statistics |
| `python main.py webui` | Start HITL Web UI |

## Configuration

Edit `.env` or `config/silra_api.yaml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `SILRA_API_KEY` | — | Silra API key |
| `SILRA_API_BASE_URL` | https://api.silra.cn/v1 | API endpoint |
| `DAEMON_TICK_INTERVAL_MINUTES` | 5 | Daemon tick interval |
| `CIRCUIT_BREAKER_HEALTH_THRESHOLD` | 60 | Health threshold for circuit breaker |
