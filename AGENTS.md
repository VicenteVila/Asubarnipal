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
├── dashboard.py                  # Streamlit (12 tabs)
├── api/main.py                   # FastAPI (port 8000)
├── app/service.py                # Agent orchestration
├── core/
│   ├── llm_router.py             # Ollama/Gemini/Brave routers
│   ├── memory.py                 # Persistent memory (legacy flat JSON)
│   ├── memory_tree.py            # H-Mem temporal-semantic tree (L0-L3)
│   ├── entity_graph.py           # H-Mem entity knowledge graph
│   ├── hybrid_retriever.py       # H-Mem hybrid retrieval (tree + graph)
│   ├── background_manager.py     # Heartbeat/Suture/Graph/Graphify rituals
│   ├── vault_manager.py          # Multi-vault management
│   ├── turboquant_engine.py      # LLM optimization
│   ├── wiki.py                   # Wiki SQLite operations
│   ├── wiki_healer.py            # Orphan detection/repair
│   ├── graph_builder.py          # Vector relationships
│   ├── graphify_integration.py   # Graphify CLI wrapper (extract/query/export)
│   ├── stt.py                    # Speech-to-text (Whisper)
│   ├── vision.py                 # Vision/OCR analysis
│   ├── cache.py                  # File-based query cache with TTL
│   ├── rate_limiter.py           # Token bucket rate limiter
│   ├── backup_manager.py         # Auto-backup with rotation & restore
│   ├── live_activity.py          # Live activity tracker
│   ├── logging_config.py         # JSON structured logging
│   ├── research_scheduler.py     # Scheduled research jobs
│   └── dashboard_logic.py        # Metrics
├── interface/
│   ├── telegram_bot.py           # Bot entrypoint
│   └── handlers/                 # Modular command handlers
│       ├── comandos.py           # /start, /status, /manual, /reporte, /model
│       ├── wiki.py               # /query, /hubs, /clusters, /lint, /quality, /queryhybrid
│       ├── busqueda.py           # /ingest, /investigar
│       ├── chat.py               # /charlar (5 modes)
│       ├── agente.py             # /agente, /rate, /calidad
│       ├── hmem_commands.py      # H-Mem system handlers (6 commands)
│       ├── graphify_handler.py   # Graphify knowledge graph handlers (7 commands)
│       ├── scheduled_research.py # Scheduled research handlers (4 commands)
│       ├── vision.py             # Vision and OCR handlers (2 commands)
│       ├── backup.py             # Backup and restore handlers (5 commands)
│       └── vault.py              # Vault management (9 commands)
├── skills/
│   ├── default_skills.py         # 39 operational skills
│   ├── vault_skills.py           # 8 vault management skills
│   └── optimize_llm.py           # 5 TurboQuant skills
├── index/rag.py                  # FAISS + sentence-transformers
├── tests/                        # pytest (179 passing across 15 files + 30 evaluation scenarios)
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
RAG_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
OBSIDIAN_PATH=C:\Obsidian  # External Obsidian vault
```

**Required**: `TELEGRAM_TOKEN`, `OLLAMA_BASE_URL`. Others optional.

## Telegram Bot Commands (49 total)

### Basic & System Commands (5)
| Command | Description |
|---------|-------------|
| `/start` | Welcome message with project history |
| `/manual` | Send operations manual |
| `/status` | System telemetry (CPU, RAM, heartbeat, Brave limit) |
| `/reporte` | Agent self-reflection report |
| `/model [ollama|gemini|auto]` | Show or switch LLM model |

### Session & Evaluation Commands (4)
| Command | Description |
|---------|-------------|
| `/session` | Show session information (messages, tokens, mode, model) |
| `/clear_session` | Clear user chat history from database |
| `/rate <1-5>` | Manually rate the precision of the last response |
| `/calidad` | Show rating and evaluation statistics (accuracy, si/no/ms counts) |

### Wiki & Search Commands (9)
| Command | Description |
|---------|-------------|
| `/ingest <url\|path>` | Ingest web URL, YouTube video, local file, or attached PDF/Image |
| `/investigar <topic>` | Deep research via Brave Search and auto-ingestion |
| `/query <question>` | Search wiki (RAG) with inline action buttons |
| `/queryhybrid <question>` | Hybrid search SQLite + Obsidian wiki (alias: `/hybrid`) |
| `/query_vectorial <search>` | Semantic vector search in FAISS |
| `/hubs` | Show central concept nodes of the wiki |
| `/clusters` | Show thematic communities of the wiki |
| `/lint` | Wiki health diagnostics (health score, orphan notes, broken links) |
| `/quality [limit]` | Run quality diagnostics on recent ingests |

### Chat & Agent Commands (2)
| Command | Description |
|---------|-------------|
| `/charlar <mode> <topic>` | Chat in 5 modes (libre, consultor, devil, socratico, lateral) |
| `/agente <task>` | Autonomous reasoning with tool execution (skills) |

### H-Mem Commands (5)
| Command | Description |
|---------|-------------|
| `/memoria` | H-Mem system status (tree + graph stats) |
| `/recordar <texto>` | Add memory to H-Mem system |
| `/pensar <pregunta>` | Query H-Mem with full retrieval + answer |
| `/contexto <query>` | Get memory context for prompts |
| `/entidades` | Show entity knowledge graph hubs |

### Graphify (Knowledge Graph) Commands (7)
| Command | Description |
|---------|-------------|
| `/graphify [deep]` | Build knowledge graph (regular or deep extraction) |
| `/graph_update` | Incremental update of knowledge graph |
| `/graph_query <pregunta>` | Query knowledge graph with natural language |
| `/graph_stats` | Show graph nodes, edges and densities |
| `/graph_report` | Show knowledge graph health report |
| `/graph_add <url>` | Extract concepts and add URL relations to graph |
| `/graph_export <format>` | Export graph (html, svg, graphml, wiki, callflow) |

### Scheduled Research Commands (4)
| Command | Description |
|---------|-------------|
| `/schedule <topic> [min]` | Schedule a recurring research job |
| `/schedules` | List all scheduled research jobs |
| `/cancel_schedule <id>` | Cancel a scheduled research job |
| `/toggle_schedule <id>` | Enable/disable a scheduled research job |

### Vision & OCR Commands (2)
| Command | Description |
|---------|-------------|
| `/vision [prompt]` | Analyze last photo using LLM vision (llava) |
| `/ocr` | Extract text from last photo |

### Backup Commands (5)
| Command | Description |
|---------|-------------|
| `/backup [vault]` | Backup active vault or all system data |
| `/backups` | List all available backups |
| `/restore <name>` | Restore system/vault from a backup |
| `/backup_stats` | Show backup statistics (size, count) |
| `/backup_clear` | Delete all backups |

### Vault Management Commands (6)
| Command | Description |
|---------|-------------|
| `/vaults` | List all vaults, their databases and active one |
| `/vault_create <nombre>` | Create a new vault |
| `/vault_use <nombre>` | Switch to a active vault |
| `/vault_info` | Show active vault details |
| `/vault_delete <nombre>` | Delete a vault (with backup) |
| `/vault_export [nombre]` | Export vault to JSON |

Also handles plain text messages (passes to agent with RAG context).

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_llm_router.py -v

# Run evaluation scenarios (Levels 1-4)
python -m pytest tests/evaluation/scenarios.py -v

# Coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

**Tests**: 179 passing unit/integration tests across 15 test files (including 30 end-to-end evaluation scenarios in `tests/evaluation/`).

---

## Chat Modes (/charlar)

- **libre** - Conversación natural y creativa
- **consultor** - Análisis en 3 fases: Definición → Ejecución → Evaluación
- **devil** - Crítica implacable, encuentra fallos y riesgos
- **socrático** - Guía mediante preguntas, no da respuestas directas
- **lateral** - Perspectivas alternativas de chef, músico, tribu, algoritmo

---

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

---

## Background Rituals

- **Heartbeat**: Every 60s - logs CPU/RAM to `data/heartbeat.json`
- **Suture**: Every 10min - cleans and repairs wiki
- **Graph**: Every 30min - rebuilds vector relationships
- **H-Mem**: Every 30min - consolidates tree levels and entity graph
- **Graphify**: Every 30min - rebuilds knowledge graph index

---

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

---

## Operational Skills (52 total)

- **Archivo**: run_command, read_file, write_file, list_files, search_in_files
- **Memoria**: remember, recall, get_memories, memory_stats, hmem_remember, hmem_recall, hmem_think, hmem_get_context, hmem_get_stats, hmem_get_recent
- **Evaluaciones / Feedback**: record_feedback, record_eval_feedback, set_pending_eval, get_eval_stats, get_feedback_context, set_last_response, get_last_response
- **Wiki**: get_wiki_stats, search_wiki, create_wiki_note
- **Sistema**: get_system_info, get_env, set_env, check_service, get_time
- **LLM**: list_ollama_models, pull_ollama_model
- **Herramientas**: execute_python, install_package
- **GitHub**: clone_repo
- **Traducción**: translate, detect_language
- **Research**: search_arxiv, get_audio_summary
- **Vault**: list_vaults, create_vault, switch_vault, delete_vault, export_vault, import_vault, get_active_vault, get_vault_stats
- **TurboQuant**: optimize_llm, show_turbo_status, benchmark_llm, get_recommended_context, list_available_modes

---

## Dashboard Tabs (12)

1. **Dashboard** - System telemetry, activity heatmap
2. **Skills** - 50+ available functions
3. **Wiki** - Note inventory, timeline, research proposals
4. **Raw** - Raw sources (immutable truth layer)
5. **Grafo** - Vector graph, communities, hubs
6. **Logs** - Real-time filtered agent logs
7. **Salud** - Wiki health diagnostics (broken links, orphans, stale notes)
8. **Schema** - CLAUDE.md viewer
9. **Latido** - Cron background jobs (editable)
10. **Feeds** - RSS subscriptions with alerts
11. **Analytics** - Command history + memory usage
12. **H-Mem** - H-Mem temporal-semantic tree and entity graph viewer

---

## Notable Code Locations

- `config.py:10` - Base directory and path configuration
- `interface/telegram_bot.py:69-74` - Service initialization
- `core/llm_router.py` - Multi-model LLM routing (Ollama/Gemini/Brave)
- `core/vault_manager.py` - Multiple vault management
- `core/turboquant_engine.py` - TurboQuant LLM optimization
- `skills/default_skills.py` - 39 skill definitions
- `skills/vault_skills.py` - 8 vault management skills
- `skills/optimize_llm.py` - 5 TurboQuant skills
- `index/rag.py` - Vector search engine (vault-aware)

---

## Notes

- Agent runs with tool-calling to execute skills
- RAG indexes project files for context
- Dashboard tracks metrics
- Memory persists across sessions
- Feed tracker alerts on RSS updates
- Brave Search limit: 1500/month
- Multiple vaults with separate DB and RAG indices
- TurboQuant auto-detection for chat modes

---

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