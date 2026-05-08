# AGENTS.md

## Project State

This repository is mostly a shell/placeholder. Directories `app/`, `core/`, `skills/`, `interface/`, `tests/` contain no Python files yet.

Main content is reference data in `data/turboquant/` - a separate quantization research sub-project.

## Running Tests

No tests exist yet in the main repo. The `data/turboquant/` sub-project has its own test suite:
```bash
cd data/turboquant && pytest
```

## Dependencies

Install via `venv_linux` (already present) or recreate with:
```bash
python3 -m venv venv_linux
source venv_linux/bin/activate
pip install -r requirements.txt
```

## Environment

Required variables in `.env`:
- `GEMINI_KEYS` - Google Gemini API keys (comma-separated)
- `TELEGRAM_TOKEN` - Telegram bot token
- `BRAVE_API_KEY` - Brave Search API key
- `HF_TOKEN` - HuggingFace token