"""Agent service with all recovered features."""

import json
import logging
import time
from pathlib import Path

import config
from core.llm_router import LLMRouter
from core.skill_registry import SkillRegistry
from core.background_manager import AgentState
from index.rag import RAGEngine
from core.bot_logger import logger

_agent_state = None

def get_agent_state() -> AgentState:
    global _agent_state
    if _agent_state is None:
        _agent_state = AgentState()
    return _agent_state


class HMemService:
    """
    H-Mem enhanced service.
    Wraps AgentService with hybrid memory capabilities.
    """
    
    def __init__(self) -> None:
        self.hmem = None
        self.llm = LLMRouter()
        self.skill_registry = SkillRegistry()
        self._init_hmem()
        logger.info("HMemService initialized")
    
    def _init_hmem(self) -> None:
        try:
            from core.hybrid_retriever import get_hmem_manager
            self.hmem = get_hmem_manager()
            logger.info("H-Mem manager loaded")
        except Exception as e:
            logger.warning(f"H-Mem not available: {e}")
            self.hmem = None
    
    def remember(self, content: str, metadata: dict = None) -> dict:
        """Add memory to H-Mem system."""
        if self.hmem:
            return self.hmem.remember(content, metadata)
        return {"error": "H-Mem not available"}
    
    def recall(self, query: str, time_range: tuple = None) -> dict:
        """Recall from H-Mem memory."""
        if self.hmem:
            return self.hmem.recall(query, time_range)
        return {"error": "H-Mem not available"}
    
    def think(self, query: str, context: str = None) -> str:
        """Full H-Mem query with answer."""
        if self.hmem:
            return self.hmem.think(query, context)
        return "H-Mem not available"
    
    def get_context(self, query: str) -> str:
        """Get memory context for prompts."""
        if self.hmem:
            return self.hmem.get_context(query)
        return ""
    
    def get_stats(self) -> dict:
        """Get H-Mem system stats."""
        if self.hmem:
            return self.hmem.stats()
        return {"error": "H-Mem not available"}
    
    def get_recent_memories(self, limit: int = 10) -> list:
        """Get recent memories from tree."""
        if self.hmem:
            try:
                tree = self.hmem.retriever.memory_tree
                if tree:
                    return tree.get_recent(limit=limit)
            except Exception:
                pass
        return []
    
    def get_entity_graph(self) -> dict:
        """Get entity graph stats and hubs."""
        if self.hmem:
            try:
                graph = self.hmem.retriever.entity_graph
                if graph:
                    return {
                        "stats": graph.get_stats(),
                        "hubs": graph.get_hubs(limit=10),
                    }
            except Exception:
                pass
        return {"error": "Entity graph not available"}


class AgentService:
    def __init__(self) -> None:
        self.llm = LLMRouter()
        self.skill_registry = SkillRegistry()
        self.rag = RAGEngine(config.INDEX_DIR / "index.faiss")
        self.wiki_db = None
        self.graph_store = {}
        logger.info("AgentService initialized")
    
    def agent_chat(self, message: str, hist_to_pass: list = None) -> dict:
        """Process an agent chat message."""
        start = time.time()
        agent_state = get_agent_state()
        agent_state.mark_alive()

        messages = hist_to_pass or []
        messages.append({"role": "user", "content": message})
        
        logger.incoming(f"🎯 [AGENTE] Recibido: {message[:60]}...")

        # Añadir contexto de feedback si existe
        try:
            from skills.default_skills import get_feedback_context
            fb_context = get_feedback_context()
            if fb_context.get("success") and fb_context.get("context"):
                messages.insert(0, {
                    "role": "system",
                    "content": f"[FEEDBACK CONTEXT]\n{fb_context['context']}\n[/FEEDBACK CONTEXT]"
                })
        except Exception as e:
            logger.debug(f"Could not add feedback context: {e}")

        # Añadir contexto del último source ingestado
        try:
            from core.wiki import Wiki
            wiki = Wiki()
            last_source = wiki.get_last_source()
            if last_source:
                source_context = f"[ÚLTIMO CONTENIDO INGESTADO]\nTipo: {last_source.get('tipo', 'N/A')}\nTítulo: {last_source.get('name', 'N/A')}\nFuente: {last_source.get('fuente', 'N/A')}\nContenido: {last_source.get('content', '')[:1500]}...\n[/ÚLTIMO CONTENIDO]"
                messages.insert(0, {
                    "role": "system",
                    "content": source_context
                })
        except Exception as e:
            logger.debug(f"Could not add last source context: {e}")

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
            logger.incoming("🤖 [AGENTE] Procesando con LLM...")
            result = self.llm.call_agent(messages, tools=tools)
            result["time"] = time.time() - start
            agent_state.record_success()
            
            # Log de tool calls si las hay
            tool_calls = result.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    logger.incoming(f"🔧 [TOOL CALL] {tc.get('name', 'unknown')}")
            
            logger.success(f"✅ [AGENTE] Completado en {result['time']:.2f}s | Tools: {len(tool_calls)}")

            # Guardar última respuesta para feedback
            try:
                from skills.default_skills import set_last_response, set_pending_eval
                set_last_response(message, result.get("response", ""))
                # Set pending evaluation for sí/no/ms feedback
                set_pending_eval(message, result.get("response", ""), context="agent_chat")
            except Exception:
                pass  # No critical

            logger.info(f"Agent chat completed in {result['time']:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Agent chat error: {e}: {e}")
            agent_state.record_failure(str(e))
            return {
                "response": f"Error: {e}",
                "tool_calls": [],
                "time": time.time() - start,
            }
    
    def query(self, q: str) -> dict:
        """Simple text query without tools."""
        return {"response": self.llm.generate(q), "query": q}
    
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


class AsubarnipalService:
    """Extended service with wiki, research, and graph features."""
    
    def __init__(self) -> None:
        self.llm = LLMRouter()
        self.skill_registry = SkillRegistry()
        self.rag = RAGEngine(config.INDEX_DIR / "index.faiss")
        self._init_wiki()
        logger.info("AsubarnipalService initialized")
    
    def _init_wiki(self) -> None:
        """Initialize wiki database."""
        try:
            import sqlite3
            self.wiki_conn = sqlite3.connect(str(config.WIKI_PATH))
            self.wiki_cursor = self.wiki_conn.cursor()
            self._ensure_wiki_tables()
            logger.info("Wiki initialized")
        except Exception as e:
            logger.warning(f"Wiki not available: {e}")
            self.wiki_conn = None
    
    def _ensure_wiki_tables(self) -> None:
        """Ensure wiki tables exist."""
        if not self.wiki_conn:
            return
        try:
            self.wiki_cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    type TEXT,
                    content TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.wiki_cursor.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY,
                    from_entity INTEGER,
                    to_entity INTEGER,
                    relation_type TEXT,
                    FOREIGN KEY(from_entity) REFERENCES entities(id),
                    FOREIGN KEY(to_entity) REFERENCES entities(id)
                )
            """)
            self.wiki_conn.commit()
        except Exception as e:
            logger.warning(f"Table creation error: {e}")
    
    def query_wiki(self, query: str) -> dict:
        """Query the wiki."""
        if not self.wiki_conn:
            return {"error": "Wiki not available"}
        
        try:
            self.wiki_cursor.execute(
                "SELECT name, type, content FROM entities WHERE content LIKE ?",
                (f"%{query}%",)
            )
            results = self.wiki_cursor.fetchall()
            return {"results": [{"name": r[0], "type": r[1], "content": r[2]} for r in results]}
        except Exception as e:
            return {"error": str(e)}
    
    def add_entity(self, name: str, entity_type: str, content: str, metadata: dict = None) -> dict:
        """Add entity to wiki."""
        if not self.wiki_conn:
            return {"error": "Wiki not available"}
        
        try:
            meta_json = json.dumps(metadata) if metadata else "{}"
            self.wiki_cursor.execute(
                "INSERT OR REPLACE INTO entities (name, type, content, metadata) VALUES (?, ?, ?, ?)",
                (name, entity_type, content, meta_json)
            )
            self.wiki_conn.commit()
            return {"success": True, "name": name}
        except Exception as e:
            return {"error": str(e)}
    
    def add_relation(self, from_entity: str, to_entity: str, relation_type: str) -> dict:
        """Add relation to knowledge graph."""
        if not self.wiki_conn:
            return {"error": "Wiki not available"}
        
        try:
            self.wiki_cursor.execute(
                "SELECT id FROM entities WHERE name = ?", (from_entity,)
            )
            from_id = self.wiki_cursor.fetchone()
            self.wiki_cursor.execute(
                "SELECT id FROM entities WHERE name = ?", (to_entity,)
            )
            to_id = self.wiki_cursor.fetchone()
            
            if from_id and to_id:
                self.wiki_cursor.execute(
                    "INSERT INTO relations (from_entity, to_entity, relation_type) VALUES (?, ?, ?)",
                    (from_id[0], to_id[0], relation_type)
                )
                self.wiki_conn.commit()
                return {"success": True}
            return {"error": "Entities not found"}
        except Exception as e:
            return {"error": str(e)}
    
    def ingest_url(self, url: str) -> dict:
        """Ingest content from URL."""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            resp = requests.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string if soup.title else url
            text = soup.get_text()[:10000]
            
            return self.add_entity(
                name=title,
                entity_type="webpage",
                content=text,
                metadata={"url": url}
            )
        except Exception as e:
            return {"error": str(e)}
    
    def research_topic(self, topic: str) -> dict:
        """Research a topic automatically."""
        from core.llm_router import BraveRouter
        
        brave = BraveRouter()
        
        search_results = brave.search(topic, num_results=5)
        
        entities = []
        for result in search_results:
            entity = self.add_entity(
                name=result.get("title", topic),
                entity_type="research_source",
                content=result.get("description", ""),
                metadata={"url": result.get("url", ""), "topic": topic}
            )
            entities.append(entity)
        
        return {
            "topic": topic,
            "sources": search_results,
            "entities_saved": len(entities)
        }
    
    def get_graph(self) -> dict:
        """Get knowledge graph."""
        if not self.wiki_conn:
            return {"error": "Wiki not available"}
        
        try:
            self.wiki_cursor.execute("""
                SELECT e1.name, r.relation_type, e2.name 
                FROM relations r
                JOIN entities e1 ON r.from_entity = e1.id
                JOIN entities e2 ON r.to_entity = e2.id
            """)
            relations = self.wiki_cursor.fetchall()
            return {
                "nodes": [],
                "edges": [{"from": r[0], "type": r[1], "to": r[2]} for r in relations]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def query(self, q: str) -> dict:
        """Process a query."""
        return self.agent_chat(q)
    
    def agent_chat(self, message: str, hist_to_pass: list = None) -> dict:
        """Process an agent chat message."""
        start = time.time()
        agent_state = get_agent_state()
        agent_state.mark_alive()
        
        messages = hist_to_pass or []
        messages.append({"role": "user", "content": message})
        
        tools = self.skill_registry.get_tools()
        
        try:
            result = self.llm.call_agent(messages, tools=tools)
            result["time"] = time.time() - start
            agent_state.record_success()
            logger.info(f"Agent chat completed in {result['time']:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Agent chat error: {e}: {e}")
            agent_state.record_failure(str(e))
            return {
                "response": f"Error: {e}",
                "tool_calls": [],
                "time": time.time() - start,
            }


