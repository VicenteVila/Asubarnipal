import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

GEMINI_KEYS = os.getenv("GEMINI_KEYS", "").split(",") if os.getenv("GEMINI_KEYS") else []
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

RAG_MODEL = os.getenv("RAG_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RAG_DEVICE = os.getenv("RAG_DEVICE", "cpu")

DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "index"
STORAGE_DIR = BASE_DIR / "storage"

WIKI_PATH = DATA_DIR / "wiki.db"
WIKI_DIR = DATA_DIR / "wiki"
GRAPH_STORE = DATA_DIR / "graph_store"
VECTOR_INDEX = DATA_DIR / "vector.index"

LOG_FILE = DATA_DIR / "agente.log"