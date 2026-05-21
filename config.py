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
TEMP_DIR = BASE_DIR / "temp"
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
OLLAMA_MODELS = os.getenv("OLLAMA_MODELS", "/mnt/c/Users/Vicente/.ollama/models")

# OCR — modelo Ollama usado para extraer texto de imágenes y PDFs escaneados
# Asegúrate de tenerlo disponible: ollama pull glm-ocr:latest
OCR_MODEL = os.getenv("OCR_MODEL", "glm-ocr:latest")

GEMINI_KEYS = [k.strip() for k in os.getenv("GEMINI_KEYS", "").split(",") if k.strip()]
GEMINI_CURRENT = 0
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

RAG_MODEL = os.getenv("RAG_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
RAG_DEVICE = os.getenv("RAG_DEVICE", "cpu")

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "auto")

ENABLE_HEARTBEAT = os.getenv("ENABLE_HEARTBEAT", "true").lower() == "true"
HEARTBEAT_INTERVAL = 60
SUTURE_INTERVAL = 600
GRAPH_INTERVAL = 1800

BRAVE_MONTHLY_LIMIT = 1500

# TurboQuant Settings
TURBOQUANT_ENABLED = os.getenv("TURBOQUANT_ENABLED", "true").lower() == "true"
TURBOQUANT_DEFAULT_MODE = os.getenv("TURBOQUANT_DEFAULT_MODE", "consultor")
TURBOQUANT_AUTO_DETECT = os.getenv("TURBOQUANT_AUTO_DETECT", "true").lower() == "true"

# Top 3 models to optimize (from user's ollama list)
TURBOQUANT_TOP_MODELS = [
    "qwen3.5:4b",
    "qwen3:8b",
    "gemma4:e4b",
]

def ensure_directories():
    """Crea directorios necesarios si no existen."""
    dirs = [DATA_DIR, INDEX_DIR, STORAGE_DIR, SKILLS_DIR, TEMP_DIR]
    for d in dirs:
        d.mkdir(exist_ok=True)
    
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(exist_ok=True)
    
    if not WIKI_DIR.exists() and OBSIDIAN_PATH.exists():
        try:
            WIKI_DIR.mkdir(exist_ok=True, parents=True)
        except Exception:
            pass

ensure_directories()