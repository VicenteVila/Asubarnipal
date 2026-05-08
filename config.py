"""Configuration for Asubarnipal V2."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]
GEMINI_CURRENT = 0
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

RAG_MODEL = os.getenv("RAG_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RAG_DEVICE = os.getenv("RAG_DEVICE", "cpu")

DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "index"
STORAGE_DIR = BASE_DIR / "storage"
SKILLS_DIR = BASE_DIR / "skills"

WIKI_PATH = DATA_DIR / "wiki.db"
WIKI_DIR = DATA_DIR / "wiki"
RAW_DIR = DATA_DIR / "raw"
GRAPH_STORE = DATA_DIR / "graph_store"
VECTOR_INDEX = DATA_DIR / "vector.index"
HEARTBEAT_FILE = DATA_DIR / "heartbeat.json"
AGENT_STATE_FILE = DATA_DIR / "agent_state.json"
BRAVE_COUNTER_FILE = DATA_DIR / "brave_counter.json"
OBSIDIAN_PATH = Path(os.getenv("OBSIDIAN_PATH", r"C:\Obsidian"))
GRAPH_STORE_PATH = OBSIDIAN_PATH / "graph_store"

LOG_FILE = DATA_DIR / "agente.log"

MANUAL_FILE = DATA_DIR / "manual_agente.md"

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "auto")

ENABLE_HEARTBEAT = os.getenv("ENABLE_HEARTBEAT", "true").lower() == "true"
HEARTBEAT_INTERVAL = 60
SUTURE_INTERVAL = 600
GRAPH_INTERVAL = 1800

BRAVE_MONTHLY_LIMIT = 1500