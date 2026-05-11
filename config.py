"""Configuration for Asubarnipal V2."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# Rutas base - Auto-detectar según SO
if os.name == 'nt':  # Windows
    DEFAULT_OBSIDIAN = r"C:\Obsidian"
else:  # Linux/Mac/WSL
    DEFAULT_OBSIDIAN = "/mnt/c/Obsidian"

OBSIDIAN_PATH = Path(os.getenv("OBSIDIAN_PATH", DEFAULT_OBSIDIAN))
WIKI_DIR = OBSIDIAN_PATH / "wiki"
RAW_DIR = OBSIDIAN_PATH / "raw"
GRAPH_STORE_PATH = OBSIDIAN_PATH / "graph_store"

# Datos locales
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "index"
STORAGE_DIR = BASE_DIR / "storage"
SKILLS_DIR = BASE_DIR / "skills"
STORAGE_DIR.mkdir(exist_ok=True)

WIKI_PATH = DATA_DIR / "wiki.db"
VECTOR_INDEX = DATA_DIR / "vector.index"
HEARTBEAT_FILE = DATA_DIR / "heartbeat.json"
AGENT_STATE_FILE = DATA_DIR / "agent_state.json"
BRAVE_COUNTER_FILE = DATA_DIR / "brave_counter.json"

LOG_FILE = DATA_DIR / "agente.log"

MANUAL_FILE = DATA_DIR / "manual_agente.md"

# LLM
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]
GEMINI_CURRENT = 0
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

RAG_MODEL = os.getenv("RAG_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RAG_DEVICE = os.getenv("RAG_DEVICE", "cpu")

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "auto")

ENABLE_HEARTBEAT = os.getenv("ENABLE_HEARTBEAT", "true").lower() == "true"
HEARTBEAT_INTERVAL = 60
SUTURE_INTERVAL = 600
GRAPH_INTERVAL = 1800

BRAVE_MONTHLY_LIMIT = 1500