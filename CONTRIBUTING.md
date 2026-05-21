# Contributing to Asubarnipal

Thank you for your interest in contributing to Asubarnipal.

## Development Setup

```bash
# Clone and set up
git clone https://github.com/VicenteVila/Asubarnipal.git
cd Asubarnipal
python -m venv venv_linux
source venv_linux/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov ruff

# Run tests
python -m pytest tests/ -v

# Lint
ruff check .
ruff format .
```

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass: `python -m pytest tests/ -v`
4. Run linter: `ruff check .`
5. Submit PR with clear description of changes

## Code Style

- **Language**: Code/comments in English, UI/messages in Spanish
- **Formatting**: ruff (auto-formatted)
- **Type hints**: Required for all public functions
- **Imports**: Standard library first, then third-party, then local

## Commit Messages

Follow conventional commits:

```
feat: add voice message transcription
fix: handle empty wiki search results
docs: update README with Docker instructions
chore: remove deprecated files
test: add coverage for query handlers
```

## Architecture

```
interface/     → Telegram bot + handlers
core/          → Business logic (LLM, memory, wiki, background)
app/           → Agent service orchestration
index/         → RAG engine (FAISS + BM25)
skills/        → Tool definitions
api/           → REST API (FastAPI)
tests/         → pytest suite
```

## Testing

- All PRs must pass 110+ tests
- New features require test coverage
- Mock external services (Ollama, Telegram API)

```bash
# Run all tests
python -m pytest tests/ -v

# Coverage report
python -m pytest tests/ --cov=. --cov-report=term-missing
```

## Reporting Issues

- **Bugs**: Use the bug report template
- **Features**: Use the feature request template
- Include: Python version, OS, error logs, reproduction steps
