.PHONY: help install bot dashboard api test lint format clean venv

help:
	@echo "Asubarnipal - Available commands:"
	@echo ""
	@echo "  make install     Install all dependencies"
	@echo "  make venv        Create virtual environment"
	@echo "  make bot         Start Telegram bot"
	@echo "  make dashboard   Start Streamlit dashboard"
	@echo "  make api         Start FastAPI REST server"
	@echo "  make test        Run all tests"
	@echo "  make test-cov    Run tests with coverage"
	@echo "  make lint        Run linter (ruff)"
	@echo "  make format      Format code (ruff)"
	@echo "  make clean       Remove cache and temp files"

install:
	pip install -r requirements.txt

venv:
	python -m venv .venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source .venv/bin/activate  (Linux/macOS)"
	@echo "  .venv\Scripts\activate     (Windows)"

bot:
	python -m interface.telegram_bot

dashboard:
	streamlit run dashboard.py

api:
	python -m api.main

test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

lint:
	ruff check .

format:
	ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .pytest_cache/ .ruff_cache/ htmlcov/ .coverage
	rm -rf build/ dist/ *.egg-info/
	@echo "Cleaned up cache and temp files"
