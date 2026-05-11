# AGENTS.md

## Project Structure

```
Asubarnipal/
├── api/main.py              # FastAPI REST server (port 8000)
├── app/service.py          # Agent service (LLM + skills + RAG)
├── core/
│   ├── background_manager.py # Heartbeat, Suture, Graph rituals
│   ├── command_history.py  # Command analytics
│   ├── feed_tracker.py    # RSS feed subscriptions with alerts
│   ├── llm_router.py      # Ollama/Gemini/Brave routers
│   ├── memory.py          # Enhanced persistent memory
│   ├── skill_registry.py  # Skills/tools registry
│   └── dashboard_logic.py # Metrics and dashboard
├── interface/telegram_bot.py # Telegram bot (15 commands)
├── skills/default_skills.py  # 40+ operational skills
├── index/rag.py            # RAG (sentence-transformers + FAISS)
├── ingestion/             # Web content ingestion
├── processing/           # Data processing
├── storage/               # Memory, feeds, state files
├── data/wiki/             # Wiki notes (SQLite)
├── dashboard.py           # Streamlit dashboard (11 tabs)
├── config.py              # Configuration
└── .env                   # Environment variables
```

## Running the Agent

### Start the Telegram Bot
```bash
# Windows
.venv\Scripts\activate
python -m interface.telegram_bot

# Linux
source venv_linux/bin/activate
python -m interface.telegram_bot
```

### Start Dashboard
```bash
streamlit run dashboard.py
```

### Start API (optional)
```bash
python -m api.main
# API at http://localhost:8000
```

### Environment Variables (.env)

```bash
TELEGRAM_TOKEN=your_bot_token
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:4b
GEMINI_KEYS=key1,key2
BRAVE_API_KEY=your_key
HF_TOKEN=your_token
RAG_MODEL=sentence-transformers/all-MiniLM-L6-v2
OBSIDIAN_PATH=C:\Obsidian  # External Obsidian vault
```

## Telegram Bot Commands (15 total)

| Command | Description |
|---------|-------------|
| `/start` | Welcome message with project history |
| `/manual` | Send operations manual |
| `/status` | System telemetry (CPU, RAM, heartbeat, Brave limit) |
| `/reporte` | Agent self-reflection report |
| `/model [ollama\|gemini\|auto]` | Show or switch LLM model |
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

Also handles plain text messages (passes to agent with RAG context).

## Chat Modes (/charlar)

- **libre** - Conversación natural y creativa
- **consultor** - Análisis en 3 fases: Definición → Ejecución → Evaluación
- **devil** - Crítica implacable, encuentra fallos y riesgos
- **socrático** - Guía mediante preguntas, no da respuestas directas
- **lateral** - Perspectivas alternativas de chef, músico, tribu, algoritmo

## Background Rituals

- **Heartbeat**: Every 60s - logs CPU/RAM to `data/heartbeat.json`
- **Suture**: Every 10min - cleans and repairs wiki
- **Graph**: Every 30min - rebuilds vector relationships

## Memory System

```python
from core.memory import EnhancedMemory

memory = EnhancedMemory()

# Remember something
memory.add("Important fact", category="fact", priority=8, importance="high")

# Search memories
results = memory.search("query", limit=10)

# Get recent
recent = memory.get_recent(10, category="fact")
```

## Operational Skills (45+)

- **Archivo**: run_command, read_file, write_file, list_files, search_in_files
- **Memoria**: remember, recall, get_memories, memory_stats
- **Wiki**: get_wiki_stats, search_wiki, create_wiki_note
- **Sistema**: get_system_info, get_env, set_env, check_service
- **LLM**: list_ollama_models, pull_ollama_model
- **Herramientas**: execute_python, install_package
- **GitHub**: clone_repo
- **Traducción**: translate, detect_language
- **Research**: search_arxiv, get_audio_summary

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

## Key Dependencies

- **Ollama**: Must be running locally for LLM
- **Obsidian Vault**: External folder referenced by `OBSIDIAN_PATH` env var
- **FAISS index**: Built from wiki notes at `data/vector.index`
- **SQLite**: Wiki stored at `data/wiki.db`

## Dual Virtual Environments

- `.venv/` - Windows virtual environment
- `venv_linux/` - Linux virtual environment

Always activate the appropriate venv for your platform before running.

## Notable Code Locations

- `config.py:10` - Base directory and path configuration
- `interface/telegram_bot.py:69-74` - Service initialization
- `core/llm_router.py` - Multi-model LLM routing (Ollama/Gemini/Brave)
- `skills/default_skills.py` - 40+ skill definitions
- `index/rag.py` - Vector search engine

## Notes

- Agent runs with tool-calling to execute skills
- RAG indexes project files for context
- Dashboard tracks metrics
- Memory persists across sessions
- Feed tracker alerts on RSS updates
- Brave Search limit: 1500/month