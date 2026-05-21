# Asubarnipal - Examples

Usage examples and scripts for the Asubarnipal AI Agent.

## Quick Start Examples

### 1. Basic Agent Query

```python
"""Example: Query the agent with a question."""
from app.service import AsubarnipalService

service = AsubarnipalService()
response = service.query("What is machine learning?")
print(response)
```

### 2. Web Research

```python
"""Example: Deep research on a topic."""
from app.service import AsubarnipalService

service = AsubarnipalService()
results = service.search_web("latest advances in quantum computing")
for result in results:
    print(f"- {result['title']}: {result['url']}")
```

### 3. Wiki Ingestion

```python
"""Example: Ingest a URL into the wiki."""
from app.service import AsubarnipalService

service = AsubarnipalService()
service.index_docs("https://arxiv.org/abs/1706.03762")  # Attention Is All You Need
```

### 4. H-Mem Memory Operations

```python
"""Example: Use H-Mem to remember and recall information."""
from app.service import HMemService

hmem = HMemService()

# Add a memory
hmem.remember("Python is a versatile programming language", metadata={"category": "tech"})

# Recall memories
memories = hmem.recall("programming languages")
for mem in memories:
    print(f"- {mem['text']}")

# Think (query with answer generation)
answer = hmem.think("What do I know about Python?")
print(answer)
```

### 5. Chat Modes

```python
"""Example: Use different chat modes."""
from app.service import AgentService

agent = AgentService()

# Consultant mode
response = agent.agent_chat("Explain blockchain", mode="consultor")
print(response)

# Devil's advocate mode
response = agent.agent_chat("Should we use microservices?", mode="devil")
print(response)

# Socratic mode
response = agent.agent_chat("What is consciousness?", mode="socratico")
print(response)
```

### 6. Vault Management

```python
"""Example: Create and switch between vaults."""
from core.vault_manager import VaultManager

vm = VaultManager()

# List existing vaults
vaults = vm.list_vaults()
print(f"Available vaults: {vaults}")

# Create a new vault
vm.create("research_project", "/path/to/research/vault")

# Switch to a vault
vm.switch("research_project")
print(f"Active vault: {vm.active_vault}")
```

### 7. REST API Usage

```python
"""Example: Use the FastAPI REST API."""
import requests

BASE_URL = "http://localhost:8000"

# Health check
health = requests.get(f"{BASE_URL}/health")
print(health.json())

# Get wiki stats
stats = requests.get(f"{BASE_URL}/stats")
print(stats.json())

# Execute a command
response = requests.post(f"{BASE_URL}/command", json={"command": "query", "args": "What is AI?"})
print(response.json())
```

### 8. Vector Search

```python
"""Example: Semantic vector search."""
from index.rag import RAGEngine

rag = RAGEngine()

# Search for similar documents
results = rag.search("neural networks and deep learning", top_k=5)
for result in results:
    print(f"- Score: {result['score']:.3f} | {result['text'][:100]}...")
```

### 9. Wiki Health Check

```python
"""Example: Check wiki health and fix issues."""
from core.wiki_healer import WikiHealer

healer = WikiHealer()

# Run diagnostics
health = healer.lint()
print(f"Orphan notes: {health['orphans']}")
print(f"Broken links: {health['broken_links']}")

# Auto-repair
healer.suture()
```

### 10. LLM Router

```python
"""Example: Route requests to different LLM providers."""
from core.llm_router import get_llm_router

# Use Ollama (local)
ollama = get_llm_router("ollama")
response = ollama.chat([{"role": "user", "content": "Hello!"}])
print(response["response"])

# Use Gemini (cloud)
gemini = get_llm_router("gemini")
response = gemini.chat([{"role": "user", "content": "What is AI?"}])
print(response["response"])
```

## Advanced Examples

### Building a Custom Skill

```python
"""Example: Create and register a custom skill."""
from skills.default_skills import SkillRegistry

registry = SkillRegistry()

@registry.register("weather")
def get_weather(location: str) -> str:
    """Get weather for a location."""
    # Implementation here
    return f"Weather in {location}: Sunny, 25C"

# Use the skill
result = registry.execute("weather", {"location": "Madrid"})
print(result)
```

### Batch Document Processing

```python
"""Example: Process multiple documents at once."""
from app.service import AsubarnipalService

service = AsubarnipalService()

urls = [
    "https://arxiv.org/abs/1706.03762",
    "https://arxiv.org/abs/1810.04805",
    "https://arxiv.org/abs/2005.14165",
]

for url in urls:
    print(f"Ingesting: {url}")
    service.index_docs(url)
    print("Done!")
```

### Custom Dashboard Metrics

```python
"""Example: Add custom metrics to the dashboard."""
import streamlit as st
from core.dashboard_logic import DashboardMetrics

metrics = DashboardMetrics()

# Get custom metrics
cpu_usage = metrics.get_cpu_usage()
memory_usage = metrics.get_memory_usage()
wiki_size = metrics.get_wiki_size()

st.metric("CPU Usage", f"{cpu_usage}%")
st.metric("Memory Usage", f"{memory_usage}%")
st.metric("Wiki Size", f"{wiki_size} notes")
```

## Running Examples

```bash
# Activate virtual environment
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# Run any example
python examples/basic_query.py
python examples/hmem_demo.py
python examples/vault_management.py
```

## Requirements

All examples require the same dependencies as the main project. Install with:

```bash
pip install -r requirements.txt
```
