# AGENTS.md

**Agent-focused instruction file for Asubarnipal - AI agent with Telegram interface + RAG + Dashboard.**

## Quick Commands

```bash
# Activate virtualenv (platform-dependent)
Windows: .venv\Scripts\activate
Linux:   source venv_linux/bin/activate

# Run services
python -m interface.telegram_bot   # Telegram bot
streamlit run dashboard.py         # Dashboard (port 8501)
python -m api.main                 # REST API (port 8000)
```

## Project Structure

```
Asubarnipal/
├── config.py                     # Configuration + paths
├── dashboard.py                  # Streamlit (11 tabs)
├── api/main.py                   # FastAPI (port 8000)
├── app/service.py                # Agent orchestration
├── core/
│   ├── llm_router.py             # Ollama/Gemini/Brave routers
│   ├── memory.py                 # Persistent memory (legacy flat JSON)
│   ├── memory_tree.py            # H-Mem temporal-semantic tree (L0-L3)
│   ├── entity_graph.py           # H-Mem entity knowledge graph
│   ├── hybrid_retriever.py       # H-Mem hybrid retrieval (tree + graph)
│   ├── background_manager.py     # Heartbeat/Suture/Graph rituals
│   ├── vault_manager.py          # Multi-vault management
│   ├── turboquant_engine.py      # LLM optimization
│   ├── wiki.py                   # Wiki SQLite operations
│   ├── wiki_healer.py            # Orphan detection/repair
│   ├── graph_builder.py          # Vector relationships
│   └── dashboard_logic.py        # Metrics
├── interface/
│   ├── telegram_bot.py           # Bot entrypoint
│   └── handlers/                 # Modular command handlers
│       ├── comandos.py           # /start, /status, /manual, /reporte
│       ├── wiki.py               # /query, /hubs, /clusters, /lint
│       ├── busqueda.py           # /ingest, /investigar
│       ├── chat.py               # /charlar (5 modes)
│       └── agente.py             # /agente, /model, /query_vectorial
├── skills/
│   ├── default_skills.py         # 45+ operational skills
│   ├── vault_skills.py           # Vault management
│   └── optimize_llm.py           # TurboQuant skills
├── index/rag.py                  # FAISS + sentence-transformers
├── tests/                        # pytest (57 passing)
└── data/                         # SQLite, FAISS index, logs
```

## Environment Variables (.env)

```
TELEGRAM_TOKEN=your_bot_token
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:4b
GEMINI_KEYS=key1,key2
BRAVE_API_KEY=your_key
HF_TOKEN=your_token
RAG_MODEL=sentence-transformers/all-MiniLM-L6-v2
OBSIDIAN_PATH=C:\Obsidian  # External Obsidian vault
```

**Required**: `TELEGRAM_TOKEN`, `OLLAMA_BASE_URL`. Others optional.

## Telegram Bot Commands (21 total)

| Command | Description |
|---------|-------------|
| `/start` | Welcome message with project history |
| `/manual` | Send operations manual |
| `/status` | System telemetry (CPU, RAM, heartbeat, Brave limit) |
| `/reporte` | Agent self-reflection report |
| `/model [ollama|gemini|auto]` | Show or switch LLM model |
| `/ingest <url>` | Add URL to wiki |
| `/sync_obsidian` | Import notes from external Obsidian vault |
| `/investigar <topic>` | Deep research via Brave Search |
| `/query <question>` | Search wiki |
| `/hubs` | Show central concept nodes |
| `/clusters` | Show thematic communities |
| `/lint` | Wiki health diagnostics |
| `/indexar_wiki` | Rebuild vector FAISS index |
| `/query_vectorial <search>` | Semantic vector search |
| `/charlar <modo> <topic>` | 5 chat modes |
| `/agente <task>` | Autonomous reasoning with tool execution |
| `/vaults` | List all vaults and active one |
| `/vault_create <nombre>` | Create a new vault |
| `/vault_use <nombre>` | Switch to a different vault |
| `/vault_info` | Show active vault details |
| `/vault_delete <nombre>` | Delete a vault (with backup) |
| `/vault_export [nombre]` | Export vault to JSON |
| `/vault_import <nombre> <file>` | Import vault from JSON |

Also handles plain text messages (passes to agent with RAG context).

## H-Mem Commands (6 total)

| Command | Description |
|---------|-------------|
| `/memoria` | H-Mem system status (tree + graph stats) |
| `/recordar <texto>` | Add memory to H-Mem system |
| `/pensar <pregunta>` | Query H-Mem with full retrieval + answer |
| `/contexto <query>` | Get memory context for prompts |
| `/entidades` | Show entity graph hubs |
| `/recientes [n]` | Show recent memories (default 10, max 30) |

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_llm_router.py -v

# Coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

**Tests**: 57 passing (test_llm_router.py, test_wiki.py, test_telegram_handlers.py, test_startup.py)

## Chat Modes (/charlar)

- **libre** - Conversación natural y creativa
- **consultor** - Análisis en 3 fases: Definición → Ejecución → Evaluación
- **devil** - Crítica implacable, encuentra fallos y riesgos
- **socrático** - Guía mediante preguntas, no da respuestas directas
- **lateral** - Perspectivas alternativas de chef, músico, tribu, algoritmo

## Vault Management

Multiple vaults with separate databases and RAG indices.

```python
from core.vault_manager import VaultManager

vm = VaultManager()

# List all vaults
vm.list_vaults()

# Switch vault
vm.switch("investigacion_ia")

# Create new vault
vm.create("nuevo_vault", "/path/to/vault")

# Export/Import
vm.export_vault("vault_name", "export.json")
vm.import_vault("vault_name", "export.json")
```

Each vault has:
- **Own SQLite DB**: `data/wiki_{vaultname}.db`
- **Own RAG index**: `data/index_{vaultname}.faiss`
- **Own folder**: Configured path per vault

## Background Rituals

- **Heartbeat**: Every 60s - logs CPU/RAM to `data/heartbeat.json`
- **Suture**: Every 10min - cleans and repairs wiki
- **Graph**: Every 30min - rebuilds vector relationships

## Memory System

### Legacy Memory (Flat JSON)
```python
from core.memory import EnhancedMemory

memory = EnhancedMemory()
memory.add("Important fact", category="fact", priority=8, importance="high")
results = memory.search("query", limit=10)
recent = memory.get_recent(10, category="fact")
```

### H-Mem (Hybrid Tree + Graph - NEW)
```python
from core.hybrid_retriever import get_hmem_manager

hmem = get_hmem_manager()

# Add memory
hmem.remember("Important fact", metadata={"category": "fact"})

# Query with answer
answer = hmem.think("What do I know about X?")

# Get context for prompts
context = hmem.get_context("topic")

# System stats
stats = hmem.stats()
```

**H-Mem Architecture:**
- **Tree**: Temporal-semantic hierarchy (L0-L3) with Ebbinghaus-based robustness
- **Graph**: Entity knowledge graph with multi-hop expansion
- **Retrieval**: 3-step (Planning → Tree+Graph search → Ranking)
- **Weights**: Semantic (0.4), Temporal (0.3), Robustness (0.3)

## Operational Skills (51+)

- **Archivo**: run_command, read_file, write_file, list_files, search_in_files
- **Memoria**: remember, recall, get_memories, memory_stats
- **Wiki**: get_wiki_stats, search_wiki, create_wiki_note
- **Sistema**: get_system_info, get_env, set_env, check_service
- **LLM**: list_ollama_models, pull_ollama_model
- **Herramientas**: execute_python, install_package
- **GitHub**: clone_repo
- **Traducción**: translate, detect_language
- **Research**: search_arxiv, get_audio_summary
- **Vault**: list_vaults, create_vault, switch_vault, delete_vault, export_vault, import_vault
- **TurboQuant**: optimize_llm, show_turbo_status, benchmark_llm, get_recommended_context

## Dashboard Tabs (11)

1. **Dashboard** - System telemetry, activity heatmap
2. **Skills** - 40+ available functions
3. **Wiki** - Note inventory, timeline
4. **Raw** - Raw sources
5. **Grafo** - Vector graph, communities, hubs
6. **Logs** - Agent logs
7. **Salud** - Wiki health diagnostics
8. **Schema** - CLAUDE.md viewer
9. **Latido** - Cron jobs (editable)
10. **Feeds** - RSS subscriptions with alerts
11. **Analytics** - Command history + Memory

## Notable Code Locations

- `config.py:10` - Base directory and path configuration
- `interface/telegram_bot.py:69-74` - Service initialization
- `core/llm_router.py` - Multi-model LLM routing (Ollama/Gemini/Brave)
- `core/vault_manager.py` - Multiple vault management
- `core/turboquant_engine.py` - TurboQuant LLM optimization
- `skills/default_skills.py` - 45+ skill definitions
- `skills/vault_skills.py` - Vault management skills
- `skills/optimize_llm.py` - TurboQuant optimization skills
- `index/rag.py` - Vector search engine (vault-aware)

## Notes

- Agent runs with tool-calling to execute skills
- RAG indexes project files for context
- Dashboard tracks metrics
- Memory persists across sessions
- Feed tracker alerts on RSS updates
- Brave Search limit: 1500/month
- Multiple vaults with separate DB and RAG indices
- TurboQuant auto-detection for chat modes

## Wiki Conventions (from CLAUDE.md)

- Raw sources: `/raw/` - IMMUTABLE. Agent never modifies.
- Generated wiki: `/wiki/` - Agent has full control.
- Frontmatter required for all notes:
  ```yaml
  tipo: source|entity|concept|synthesis|moc
  fuente: "source name or N/A"
  fecha_ingesta: YYYY-MM-DD
  fecha_actualizacion: YYYY-MM-DD
  estado: draft|review|final
  tags: [tag1, tag2]
  relacionados: [[Note1]], [[Note2]]
  ```
- Before creating a new note, search for existing related entities/concepts
- If source contradicts existing entity, DOCUMENT the contradiction with date
- Update index.md after EVERY ingestion operation
- Cross-reference: every note must have at least 2 outgoing or incoming wikilinks
- NEVER leave a note as orphan (no links) after ingestion