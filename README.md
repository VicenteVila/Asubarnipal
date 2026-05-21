# Asubarnipal

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-57%20passing-brightgreen.svg)](tests/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)

**Autonomous AI Agent** with Telegram interface, RAG-powered knowledge base, hybrid memory system (H-Mem), and real-time analytics dashboard.

---

## Features

- **Telegram Bot** - 28+ commands for interaction, research, and knowledge management
- **RAG Engine** - FAISS vector search with multilingual sentence transformers
- **H-Mem** - Hybrid temporal-semantic tree + entity knowledge graph memory
- **Graphify** - Interactive knowledge graph visualization + natural language queries
- **Multi-LLM** - Ollama (local), Google Gemini, Brave Search routing
- **Streamlit Dashboard** - 12 tabs with interactive graph visualization (850px window)
- **REST API** - FastAPI server with 12+ endpoints
- **Multi-Vault** - Isolated knowledge bases with separate databases and indices
- **Background Rituals** - Heartbeat, wiki repair, graph rebuilding, Graphify auto-update
- **50+ Skills** - File operations, memory, wiki, system, research, translation

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TELEGRAM BOT                              │
│                   (interface/telegram_bot.py)                     │
│          21 commands: /start /query /agente /charlar...          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     HANDLERS (modular)                           │
│  ├── comandos.py    → /start /status /manual /reporte           │
│  ├── wiki.py        → /query /hubs /clusters /lint              │
│  ├── busqueda.py    → /ingest /investigar                       │
│  ├── chat.py        → /charlar (5 modes)                        │
│  ├── agente.py      → /agente /model /query_vectorial           │
│  ├── hmem_commands.py → /memoria /recordar /pensar /contexto    │
│  └── vault.py       → /vaults /vault_create /vault_use          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       AGENT SERVICE                              │
│                        (app/service.py)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  LLMRouter   │  │SkillRegistry │  │    RAG Engine        │   │
│  │ Ollama/Gemini│  │   50+ skills │  │  FAISS + SQLite      │   │
│  │ + Brave      │  │              │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼               ▼
         ┌─────────┐   ┌─────────┐    ┌─────────────┐
         │  Core   │   │  Wiki   │    │  Dashboard  │
         │ Memory  │   │ SQLite  │    │  Streamlit  │
         │ H-Mem   │   │ FAISS   │    │   12 tabs   │
         │Background│   │ Index   │    │             │
         │ Manager  │   │         │    │             │
         └─────────┘   └─────────┘    └─────────────┘
```

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Ollama** (for local LLM inference)
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- **Brave Search API** (optional, for web research)
- **Google Gemini API** (optional, for cloud LLM fallback)

### Installation

```bash
# Clone the repository
git clone https://github.com/VicenteVila/Asubarnipal.git
cd Asubarnipal

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Pull Ollama models
ollama pull qwen3.5:4b
ollama pull glm-ocr:latest       # For OCR capabilities
```

### Configuration

Create a `.env` file in the project root:

```env
# Required
TELEGRAM_TOKEN=your_bot_token_here
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:4b

# Optional
GEMINI_KEYS=your_gemini_key_1,your_gemini_key_2
BRAVE_API_KEY=your_brave_api_key
HF_TOKEN=your_huggingface_token
OBSIDIAN_PATH=/path/to/obsidian/vault
RAG_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
```

### Running Services

```bash
# Telegram Bot (primary interface)
python -m interface.telegram_bot

# Streamlit Dashboard (port 8501)
streamlit run dashboard.py

# FastAPI REST API (port 8000)
python -m api.main
```

---

## Telegram Commands

### General Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message with project history |
| `/manual` | Send operations manual |
| `/status` | System telemetry (CPU, RAM, heartbeat, Brave limit) |
| `/reporte` | Agent self-reflection report |
| `/model [ollama\|gemini\|auto]` | Show or switch LLM model |

### Knowledge & Research

| Command | Description |
|---------|-------------|
| `/ingest <url>` | Add URL to wiki (with OCR & YouTube transcript support) |
| `/sync_obsidian` | Import notes from external Obsidian vault |
| `/investigar <topic>` | Deep research via Brave Search |
| `/query <question>` | Search wiki knowledge base |
| `/query_vectorial <search>` | Semantic vector search |
| `/indexar_wiki` | Rebuild vector FAISS index |

### Wiki Analytics

| Command | Description |
|---------|-------------|
| `/hubs` | Show central concept nodes |
| `/clusters` | Show thematic communities |
| `/lint` | Wiki health diagnostics |

### Chat Modes

| Command | Description |
|---------|-------------|
| `/charlar libre <topic>` | Natural and creative conversation |
| `/charlar consultor <topic>` | 3-phase analysis: Definition → Execution → Evaluation |
| `/charlar devil <topic>` | Relentless criticism, finds flaws and risks |
| `/charlar socrático <topic>` | Guides through questions, never gives direct answers |
| `/charlar lateral <topic>` | Alternative perspectives (chef, musician, tribe, algorithm) |

### Autonomous Agent

| Command | Description |
|---------|-------------|
| `/agente <task>` | Autonomous reasoning with tool execution |

### H-Mem Memory System

| Command | Description |
|---------|-------------|
| `/memoria` | H-Mem system status (tree + graph stats) |
| `/recordar <text>` | Add memory to H-Mem system |
| `/pensar <question>` | Query H-Mem with full retrieval + answer |
| `/contexto <query>` | Get memory context for prompts |
| `/entidades` | Show entity graph hubs |
| `/recientes [n]` | Show recent memories (default 10, max 30) |

### Vault Management

| Command | Description |
|---------|-------------|
| `/vaults` | List all vaults and active one |
| `/vault_create <name>` | Create a new vault |
| `/vault_use <name>` | Switch to a different vault |
| `/vault_info` | Show active vault details |
| `/vault_delete <name>` | Delete a vault (with backup) |
| `/vault_export [name]` | Export vault to JSON |
| `/vault_import <name> <file>` | Import vault from JSON |

---

## H-Mem: Hybrid Memory System

A novel memory architecture combining temporal-semantic hierarchy with entity knowledge graphs.

```
Tree (Temporal-Semantic)          Graph (Entity Knowledge)
├── L0: Root                      ├── Entities with properties
├── L1: Categories                ├── Multi-hop relationships
├── L2: Subcategories             ├── Community detection
└── L3: Leaf memories             └── Centrality metrics

Retrieval: Planning → Tree+Graph search → Ranking
Weights: Semantic (0.4) + Temporal (0.3) + Robustness (0.3)
```

---

## Graphify: Knowledge Graph

Interactive knowledge graph built with [graphifyy](https://github.com/safishamsi/graphify). Scans wiki notes, raw sources, and Obsidian vault to produce a queryable graph.

```
graphify-out/
├── graph.html          ← Interactive visualization (clickable nodes, filters, search)
├── GRAPH_REPORT.md     ← Summary: key concepts, surprising connections
└── graph.json          ← Full queryable graph
```

### Telegram Commands

| Command | Description |
|---------|-------------|
| `/graphify` | Build knowledge graph |
| `/graphify deep` | Deep mode (aggressive relationship extraction) |
| `/graph_update` | Update changed files only (fast) |
| `/graph_query <question>` | Query graph with natural language |
| `/graph_stats` | Show graph statistics |
| `/graph_report` | Show graph report |
| `/graph_add <url>` | Add URL to graph |
| `/graph_export <format>` | Export (html, svg, graphml, wiki, callflow) |

### Dashboard Integration

Tab **"Grafo"** → Select **"Graphify (Interactivo)"** for:
- **850px interactive visualization** — clickable nodes, community filters, search
- **Real-time stats** — nodes, edges, communities, hubs
- **Graph report** — surprising connections, suggested questions

---

## Dashboard

Access at `http://localhost:8501` after running `streamlit run dashboard.py`.

| Tab | Description |
|-----|-------------|
| **Dashboard** | System telemetry, activity heatmap |
| **Skills** | 50+ available functions |
| **Wiki** | Note inventory, timeline |
| **Raw** | Raw sources table |
| **Grafo** | Vector graph visualization, communities, hubs |
| **Logs** | Agent log viewer |
| **Salud** | Wiki health diagnostics |
| **Schema** | CLAUDE.md viewer |
| **Latido** | Cron jobs (editable) |
| **Feeds** | RSS subscriptions with alerts |
| **Analytics** | Command history + Memory |
| **H-Mem** | Hybrid memory system visualization |

---

## REST API

Access at `http://localhost:8000/docs` for Swagger UI.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/command` | POST | Execute command via SkillRegistry |
| `/status` | GET | Agent state |
| `/stats` | GET | Wiki statistics |
| `/feeds` | GET | List RSS subscriptions |
| `/feeds/subscribe` | POST | Subscribe to RSS feed |
| `/feeds/unsubscribe` | POST | Unsubscribe from RSS feed |
| `/feeds/check` | GET | Check feed updates |
| `/history` | GET | Command history |
| `/history/add` | POST | Add to history |
| `/logs` | GET | Get agent logs |

---

## Background Rituals

| Ritual | Interval | Function |
|--------|----------|----------|
| **Heartbeat** | 60s | Logs CPU/RAM to `data/heartbeat.json` |
| **Suture** | 10min | Cleans and repairs wiki, fixes orphans |
| **Graph** | 30min | Rebuilds vector relationships |
| **Graphify** | 30min | Rebuilds interactive knowledge graph with Ollama |
| **H-Mem** | 30min | Consolidates temporal-semantic tree + entity graph |

---

## Skills (50+)

| Category | Skills |
|----------|--------|
| **File** | `run_command`, `read_file`, `write_file`, `list_files`, `search_in_files` |
| **Memory** | `remember`, `recall`, `get_memories`, `memory_stats` |
| **Wiki** | `get_wiki_stats`, `search_wiki`, `create_wiki_note` |
| **System** | `get_system_info`, `get_env`, `set_env`, `check_service` |
| **LLM** | `list_ollama_models`, `pull_ollama_model` |
| **Tools** | `execute_python`, `install_package` |
| **GitHub** | `clone_repo` |
| **Translation** | `translate`, `detect_language` |
| **Research** | `search_arxiv`, `get_audio_summary` |
| **Vault** | `list_vaults`, `create_vault`, `switch_vault`, `delete_vault`, `export_vault`, `import_vault` |
| **TurboQuant** | `optimize_llm`, `show_turbo_status`, `benchmark_llm`, `get_recommended_context` |

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_llm_router.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

**Test Coverage**: 57 passing tests across 4 test modules.

---

## Project Structure

```
Asubarnipal/
├── api/
│   └── main.py                 # FastAPI REST server (port 8000)
├── app/
│   └── service.py              # Agent service (LLM + skills + RAG)
├── core/
│   ├── llm_router.py           # Ollama/Gemini/Brave routers
│   ├── memory.py               # Enhanced persistent memory
│   ├── memory_tree.py          # H-Mem temporal-semantic tree (L0-L3)
│   ├── entity_graph.py         # H-Mem entity knowledge graph
│   ├── hybrid_retriever.py     # H-Mem hybrid retrieval (tree + graph)
│   ├── background_manager.py   # Heartbeat, Suture, Graph rituals
│   ├── vault_manager.py        # Multi-vault management
│   ├── turboquant_engine.py    # LLM optimization
│   ├── wiki.py                 # Wiki SQLite operations
│   ├── wiki_healer.py          # Orphan detection/repair
│   ├── graph_builder.py        # Vector relationships
│   ├── dashboard_logic.py      # Metrics and analytics
│   ├── feed_tracker.py         # RSS feed subscriptions
│   └── ...
├── interface/
│   ├── telegram_bot.py         # Bot entrypoint
│   └── handlers/               # Modular command handlers
│       ├── comandos.py         # /start, /status, /manual, /reporte
│       ├── wiki.py             # /query, /hubs, /clusters, /lint
│       ├── busqueda.py         # /ingest, /investigar
│       ├── chat.py             # /charlar (5 modes)
│       ├── agente.py           # /agente, /model, /query_vectorial
│       ├── hmem_commands.py    # H-Mem commands
│       ├── vault.py            # Vault management commands
│       └── validators.py       # Input validators
├── skills/
│   ├── default_skills.py       # 45+ operational skills
│   ├── vault_skills.py         # Vault management skills
│   └── optimize_llm.py         # TurboQuant optimization skills
├── index/
│   └── rag.py                  # FAISS + sentence-transformers
├── dashboard.py                # Streamlit dashboard (12 tabs)
├── config.py                   # Configuration
├── requirements.txt            # Python dependencies
├── tests/                      # Unit tests (57 passing)
├── examples/                   # Usage examples
└── data/                       # SQLite, FAISS index, logs
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Author

**Vicente Vila** - AI Engineer & Researcher

- GitHub: [@VicenteVila](https://github.com/VicenteVila)
