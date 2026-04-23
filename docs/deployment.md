# Deployment Guide

## Prerequisites

- Python 3.10+
- Silra API key
- Linux/macOS/WSL2

## Setup

```bash
# 1. Clone / navigate to project
cd meta-layer-harness

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your SILRA_API_KEY
```

## Silra API Configuration

```yaml
# config/silra_api.yaml
silra_api:
  base_url: "https://api.silra.cn/v1"
  api_key_env: "SILRA_API_KEY"
  timeout_seconds: 30
  max_retries: 3
```

Set your API key:
```bash
export SILRA_API_KEY="your-key-here"
# Or add to .env file
```

## Running

```bash
# Initialize and run one tick
python main.py tick

# Run daemon loop
python -c "from main import initialize_system; s = initialize_system(); s['daemon'].run_loop()"

# Start Web UI
python main.py webui
```

## Production Deployment

```bash
# Using systemd (Linux)
sudo cp meta-layer-harness.service /etc/systemd/system/
sudo systemctl enable meta-layer-harness
sudo systemctl start meta-layer-harness

# Using Docker (alternative)
docker build -t meta-layer-harness .
docker run -d --env-file .env -p 8080:8080 meta-layer-harness
```

## Monitoring

- Health: `python main.py health`
- Stats: `python main.py stats`
- Logs: `logs/observations/`, `logs/decisions/`
