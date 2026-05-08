# AGENTS.md

## Project Structure

```
Asubarnipal/
├── app/
│   └── service.py          # Agent service (LLM + skills + RAG)
├── core/
│   ├── llm_router.py    # Ollama/Gemini/Brave routers
│   ├── skill_registry.py # Skills/tools registry
│   └── dashboard_logic.py # Metrics and dashboard
├── interface/
│   └── telegram_bot.py   # Telegram bot interface
├── skills/
│   ├── __init__.py      # Skill functions
│   └── default_skills.py
├── index/
│   └── rag.py          # RAG engine (sentence-transformers + FAISS)
├── config.py           # Configuration
└── requirements.txt   # Dependencies
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

## Architecture

1. **Telegram Bot**: Receives messages, manages conversation state
2. **Agent Service**: Routes to LLM, executes skills/tools
3. **LLM Router**: Connects to Ollama (local) or Gemini (cloud)
4. **Skill Registry**: Available tools (file operations, search, etc.)
5. **RAG Engine**: Semantic search over codebase

## Key Commands

- `/start` - Start the bot
- `/agente <question>` - Ask the agent
- Direct message - Auto-processes as agent query

## Notes

- Agent runs with tool-calling to execute skills
- RAG indexes project files for context
- Dashboard tracks metrics