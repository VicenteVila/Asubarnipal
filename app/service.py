import logging
import time
from typing import Optional

import config
from core.llm_router import LLMRouter
from core.skill_registry import SkillRegistry
from index.rag import RAGEngine

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(self):
        self.llm = LLMRouter()
        self.skill_registry = SkillRegistry()
        self.rag = RAGEngine(config.INDEX_DIR / "index.faiss")
        logger.info("AgentService initialized")
    
    def agent_chat(self, message: str, hist_to_pass: list = None) -> dict:
        """Process an agent chat message."""
        start = time.time()
        
        messages = hist_to_pass or []
        messages.append({"role": "user", "content": message})
        
        try:
            rag_results = self.rag.search(message, top_k=3)
            if rag_results:
                context = "\n".join([
                    f"- {r['document']}" for r in rag_results
                ])
                messages.insert(0, {
                    "role": "system",
                    "content": f"Documentos relevantes:\n{context}",
                })
        except Exception as e:
            logger.warning(f"RAG search failed: {e}")
        
        tools = self.skill_registry.get_tools()
        
        try:
            result = self.llm.call_agent(messages, tools=tools)
            result["time"] = time.time() - start
            logger.info(f"Agent chat completed in {result['time']:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Agent chat error: {e}", exc_info=True)
            return {
                "response": f"Error: {e}",
                "tool_calls": [],
                "time": time.time() - start,
            }
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Simple text generation."""
        return self.llm.generate(prompt, **kwargs)
    
    def search_web(self, query: str) -> list[dict]:
        """Search the web."""
        from core.llm_router import BraveRouter
        brave = BraveRouter()
        return brave.search(query)
    
    def index_docs(self, directory: str) -> dict:
        """Index a directory for RAG."""
        from pathlib import Path
        return self.rag.index_directory(Path(directory))


class AgentWithMemory(AgentService):
    def __init__(self):
        super().__init__()
        self.conversation_history = {}
    
    def get_history(self, user_id: int) -> list:
        return self.conversation_history.get(user_id, [])
    
    def add_to_history(self, user_id: int, role: str, content: str):
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append({"role": role, "content": content})
        
        if len(self.conversation_history[user_id]) > 20:
            self.conversation_history[user_id] = self.conversation_history[user_id][-20:]
    
    def clear_history(self, user_id: int):
        self.conversation_history[user_id] = []