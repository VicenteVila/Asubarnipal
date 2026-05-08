# AGENTS.md

## Project Structure

```
Asubarnipal/
├── api/
│   └── main.py              # FastAPI REST server
├── app/
│   └── service.py          # Agent service (LLM + skills + RAG)
├── core/
│   ├── background_manager.py # Heartbeat, Suture, Graph rituals
│   ├── command_history.py  # Command analytics
│   ├── feed_tracker.py    # RSS feed subscriptions with alerts
│   ├── llm_router.py      # Ollama/Gemini/Brave routers
│   ├── memory.py          # Enhanced persistent memory
│   ├── skill_registry.py  # Skills/tools registry
│   └── dashboard_logic.py # Metrics and dashboard
├── interface/
│   └── telegram_bot.py   # Telegram bot (16 commands)
├── skills/
│   ├── __init__.py       # Skill registry
│   └── default_skills.py # 40+ operational skills
├── index/
│   └── rag.py           # RAG engine (sentence-transformers + FAISS)
├── data/
│   ├── wiki/            # Wiki notes (92 notes)
│   └── raw/             # Raw sources (2 sources)
├── storage/             # Memory, feeds, state files
├── dashboard.py          # Streamlit dashboard (11 tabs)
├── config.py            # Configuration
└── requirements.txt    # Dependencies
```

## Running the Agent

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # Edit with your keys
```

### Start the Telegram Bot (Windows/Linux)
```bash
# Windows
venv\Scripts\activate
python -m interface.telegram_bot

# Linux
source venv_linux/bin/activate
python -m interface.telegram_bot
```

### Start Dashboard (11 tabs)
```bash
streamlit run dashboard.py
```

### Start API REST (optional)
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
```

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

## Memory System

Enhanced memory with categories, priority, importance:

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

## Operational Skills (40+)

- **Archivo**: run_command, read_file, write_file, list_files, search_in_files
- **Memoria**: remember, recall, get_memories, memory_stats
- **Wiki**: get_wiki_stats, search_wiki, create_wiki_note
- **Sistema**: get_system_info, get_env, set_env, check_service
- **LLM**: list_ollama_models, pull_ollama_model
- **Herramientas**: execute_python, install_package

## Key Commands

- `/start` - Start the bot
- `/manual` - Send manual
- `/status` - Show telemetry
- `/investigar <topic>` - Deep research
- `/query <question>` - Query wiki
- `/indexar_wiki` - Rebuild vector index
- `/query_vectorial <search>` - Semantic search
- `/hubs` - Show central concepts
- `/clusters` - Show communities
- `/lint` - Diagnostics
- `/agente <task>` - Autonomous reasoning
- And 5 more commands...

## Notes

- Agent runs with tool-calling to execute skills
- RAG indexes project files for context
- Dashboard tracks metrics
- Memory persists across sessions
- Feed tracker alerts on RSS updates