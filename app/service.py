"""Agent service with all recovered features."""

import logging
import time
from pathlib import Path

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
        self.wiki_db = None
        self.graph_store = {}
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
    
    def __init__(self):
        self.llm = LLMRouter()
        self.skill_registry = SkillRegistry()
        self.rag = RAGEngine(config.INDEX_DIR / "index.faiss")
        self._init_wiki()
        logger.info("AsubarnipalService initialized")
    
    def _init_wiki(self):
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
    
    def _ensure_wiki_tables(self):
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
        
        messages = hist_to_pass or []
        messages.append({"role": "user", "content": message})
        
        tools = self.skill_registry.get_tools()
        
        try:
            result = self.llm.call_agent(messages, tools=tools)
            result["time"] = time.time() - start
            return result
        except Exception as e:
            return {
                "response": f"Error: {e}",
                "tool_calls": [],
                "time": time.time() - start,
            }


import json


class WikiReader:
    """Read from wiki database."""
    
    def __init__(self, config):
        self.wiki_path = Path(config.WIKI_PATH)
        self.conn = None
        self._connect()
    
    def _connect(self):
        try:
            import sqlite3
            self.conn = sqlite3.connect(str(self.wiki_path))
        except Exception as e:
            logger.warning(f"Cannot connect to wiki: {e}")
    
    def search(self, query: str) -> list:
        """Search wiki."""
        if not self.conn:
            return []
        try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT name, content FROM entities WHERE content LIKE ?",
                    (f"%{query}%",)
                )
                return cursor.fetchall()
            except:
                return []
    
    def get_all(self, limit: int = 100) -> list:
        """Get all wiki entries."""
        if not self.conn:
            return []
        try:
                cursor = self.conn.cursor()
                cursor.execute(f"SELECT name, type, content FROM entities LIMIT {limit}")
                return cursor.fetchall()
            except:
                return []