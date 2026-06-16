# Quick Start

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) running locally (e.g., `ollama run qwen3.5:4b`)
- Telegram bot token from [@BotFather](https://t.me/BotFather)

## Setup

```bash
# 1. Clone
git clone https://github.com/VicenteVila/Asubarnipal.git
cd Asubarnipal

# 2. Environment
cp .env.example .env
# Edit .env: set TELEGRAM_TOKEN, OLLAMA_BASE_URL

# 3. Install
pip install -r requirements.txt

# 4. Run
python -m interface.telegram_bot           # Telegram bot
streamlit run dashboard.py                  # Dashboard (port 8501)
python -m api.main                          # REST API (port 8000)
```

## Docker

```bash
docker compose up -d
```

## First Commands

- `/start` — Welcome
- `/status` — System telemetry
- `/ingest <url>` — Ingest a webpage
- `/query <question>` — Search the wiki
- `/charlar libre <topic>` — Chat with the agent
