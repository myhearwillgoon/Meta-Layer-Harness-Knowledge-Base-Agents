# Meta Layer Harness Architecture

Production-grade AI Operations System with Meta-Cognitive Harness Layer.

## Architecture

```
Level 3: Human Oversight Layer (HITL审核)
  ↓
Level 2: Meta-Cognitive Harness Agent
  ├── Observer (6 观测点)
  ├── Evaluator (冲突检测/置信度/影响分析)
  └── Intervener (输出标记/熔断/HITL)
  ↓
Level 1: Object Level Agents
  ├── Daemon (5-min tick)
  ├── Email Agent (Call #1 → Call #2 → Call #3)
  ├── Knowledge Agent
  ├── Reply Agent
  └── Goal Agent
```

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd meta-layer-harness
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Silra API key:
# SILRA_API_KEY=sk-your-api-key-here
```

### 3. Setup Knowledge Base

**The knowledge base contains 77 private Markdown files that are NOT included in this repository.**

To set up:

1. **Contact project administrator** for the knowledge base files
2. **Place files** in `knowledge-base/` subdirectories:
   - `knowledge-base/people/` - Person profiles
   - `knowledge-base/projects/` - Project documents
   - `knowledge-base/decisions/` - Meeting minutes, memos
   - `knowledge-base/vendors/` - External vendors
   - `knowledge-base/policies/` - Company policies
3. **See `knowledge-base/README.md`** for file naming conventions

### 4. Initialize System

```bash
# Index knowledge base and start
python main.py

# View system statistics
python main.py stats

# Run health check
python main.py health
```

### 5. Process Email (Example)

```python
from main import initialize_system

system = initialize_system()
result = system["email_agent"].process_email("What is our BTC allocation?")

print(f"Analysis: {result.analysis}")
print(f"Draft Reply: {result.draft_reply}")
print(f"Top Files: {result.top_files}")
```

### 6. Start Web UI (HITL)

```bash
python main.py webui
# Open http://localhost:8080
```

## Components

| Module | Description |
|--------|-------------|
| **Knowledge Base** | 77 Markdown files, SQLite index, wiki-links graph |
| **Pipeline** | 3-call LLM pipeline (relevance → query → analysis) |
| **Rule Engine** | 20 rules, 10 injection points |
| **Goal System** | Hierarchical goals with cascade completion |
| **Observer** | 6 observation points monitoring system health |
| **Evaluator** | Conflict detection (numerical/semantic/temporal/authority) |
| **Intervener** | Circuit breaker, HITL audit queue, output markers |

## Models

| Call | Model | Purpose |
|------|-------|---------|
| Call #1 | glm-4.5-air | Relevance judgment |
| Call #2 | glm-4.5-air | Search query generation |
| Call #3 | glm-4.5-air | Analysis |

## Directory Structure

```
meta-layer-harness/
├── knowledge-base/     # KB files (not in git, see setup instructions)
├── rules/              # Rule engine (rules.json + injection_points.yaml)
├── goals/              # Goal system (goals.json)
├── pipeline/           # Call #1, #2, #3
├── agents/             # Email/Knowledge/Reply/Goal/Daemon
├── harness/            # Observer/Evaluator/Intervener
├── storage/            # Indexer/VectorStore/DecisionLog
├── webui/              # HITL Web UI
├── tests/              # Integration tests
├── docs/               # API/User/Deployment docs
├── config/             # Silra API config
├── main.py             # Entry point
└── README.md           # This file
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `python main.py` | Initialize system and index KB |
| `python main.py tick` | Run one daemon tick |
| `python main.py health` | Loop health report |
| `python main.py stats` | System statistics |
| `python main.py webui` | Start HITL Web UI (port 8080) |

## Testing

```bash
# Run all tests (uses mock mode for speed)
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_e2e.py -v
```

## Documentation

- `docs/api.md` - API documentation
- `docs/user-guide.md` - User guide
- `docs/deployment.md` - Deployment guide
- `knowledge-base/README.md` - KB setup guide

## License

Internal use only.
