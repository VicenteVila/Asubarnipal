"""Background Manager - El Latido de Asubarnipal."""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class BackgroundManager:
    """Background rituals manager for Asubarnipal."""
    
    HMEM_INTERVAL = 1800
    
    def __init__(self):
        self.running = False
        self.threads = []
        self.last_heartbeat = None
        self.last_suture = None
        self.last_graph = None
        self.last_hmem = None
        self.last_graphify = None
    
    def start(self):
        """Start all background rituals."""
        if self.running:
            logger.warning("Background manager already running")
            return
        
        self.running = True
        
        if config.ENABLE_HEARTBEAT:
            t = threading.Thread(target=self._heartbeat_loop, daemon=True)
            t.start()
            self.threads.append(t)
            logger.info("💓 Heartbeat started")
        
        t = threading.Thread(target=self._suture_loop, daemon=True)
        t.start()
        self.threads.append(t)
        logger.info("💉 Suture ritual started")
        
        t = threading.Thread(target=self._graph_loop, daemon=True)
        t.start()
        self.threads.append(t)
        logger.info("🕸️ Graph ritual started")
        
        t = threading.Thread(target=self._hmem_loop, daemon=True)
        t.start()
        self.threads.append(t)
        logger.info("🌳 H-Mem consolidation ritual started")
        
        t = threading.Thread(target=self._graphify_loop, daemon=True)
        t.start()
        self.threads.append(t)
        logger.info("🕸️ Graphify knowledge graph ritual started")
    
    def stop(self):
        """Stop all background rituals."""
        self.running = False
        logger.info("Stopping background rituals...")
    
    def _heartbeat_loop(self):
        """Heartbeat - runs every minute."""
        agent_state = AgentState()
        
        while self.running:
            try:
                self._update_heartbeat()
                agent_state.mark_alive()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            time.sleep(config.HEARTBEAT_INTERVAL)
    
    def _suture_loop(self):
        """Suture - runs every 10 minutes."""
        while self.running:
            try:
                self._run_suture()
            except Exception as e:
                logger.error(f"Suture error: {e}")
            time.sleep(config.SUTURE_INTERVAL)
    
    def _graph_loop(self):
        """Graph update - runs every 30 minutes."""
        while self.running:
            try:
                self._update_graph()
            except Exception as e:
                logger.error(f"Graph error: {e}")
            time.sleep(config.GRAPH_INTERVAL)
    
    def _hmem_loop(self):
        """H-Mem consolidation - runs every 30 minutes."""
        while self.running:
            try:
                self._run_hmem_consolidation()
            except Exception as e:
                logger.error(f"H-Mem error: {e}")
            time.sleep(self.HMEM_INTERVAL)
    
    def _run_hmem_consolidation(self):
        """Consolidate H-Mem tree and update entity graph."""
        try:
            from core.hybrid_retriever import get_hmem_manager
            
            hmem = get_hmem_manager()
            
            if hmem:
                tree = hmem.retriever.memory_tree
                graph = hmem.retriever.entity_graph
                
                if tree:
                    tree.force_consolidation()
                    tree.prune_old_nodes(days=90)
                    tree_stats = tree.get_stats()
                    logger.info(f"🌳 H-Mem tree: {tree_stats.get('total_nodes', 0)} nodes")
                
                if graph:
                    graph_stats = graph.get_stats()
                    logger.info(f"🔗 H-Mem graph: {graph_stats.get('total_entities', 0)} entities, "
                               f"{graph_stats.get('total_relations', 0)} relations")
                
                self.last_hmem = {
                    "timestamp": datetime.now().isoformat(),
                    "tree_nodes": tree_stats.get("total_nodes", 0) if tree else 0,
                    "graph_entities": graph_stats.get("total_entities", 0) if graph else 0,
                }
        except ImportError:
            logger.debug("H-Mem not available for background consolidation")
        except Exception as e:
            logger.error(f"H-Mem consolidation error: {e}")
    
    def _graphify_loop(self):
        """Graphify knowledge graph update - runs every 30 minutes."""
        while self.running:
            try:
                self._update_graphify()
            except Exception as e:
                logger.error(f"Graphify error: {e}")
            time.sleep(config.GRAPH_INTERVAL)
    
    def _update_graphify(self):
        """Update knowledge graph using Graphify."""
        try:
            from core.graphify_integration import build_graph, get_graph_stats
            
            result = build_graph(backend="ollama", no_viz=False)
            
            if result.get("success"):
                stats = result.get("stats", {})
                self.last_graphify = {
                    "timestamp": datetime.now().isoformat(),
                    "nodes": stats.get("nodes", 0),
                    "edges": stats.get("edges", 0),
                    "communities": stats.get("communities", 0),
                }
                logger.info(f"🕸️ Graphify: {stats.get('nodes', 0)} nodes, "
                           f"{stats.get('edges', 0)} edges, "
                           f"{stats.get('communities', 0)} communities")
            else:
                logger.warning(f"Graphify build failed: {result.get('error', 'Unknown')}")
        except ImportError:
            logger.debug("Graphify not available")
        except Exception as e:
            logger.error(f"Graphify update error: {e}")
    
    def _update_heartbeat(self):
        """Update heartbeat.json."""
        import psutil
        
        heartbeat = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('.').percent,
            "uptime": time.time(),
        }
        
        config.HEARTBEAT_FILE.write_text(json.dumps(heartbeat, indent=2), encoding="utf-8")
        self.last_heartbeat = heartbeat
        logger.debug(f"💓 Heartbeat: CPU {heartbeat['cpu_percent']}%")
    
    def _run_suture(self):
        """Heal orphaned notes in wiki."""
        from core.wiki_healer import WikiHealer
        
        healer = WikiHealer()
        healed = healer.heal_orphans()
        
        self.last_suture = {
            "timestamp": datetime.now().isoformat(),
            "orphans_healed": healed,
        }
        logger.info(f"💉 Suture: healed {healed} orphans")
    
    def _update_graph(self):
        """Update knowledge graph."""
        from core.graph_builder import GraphBuilder
        
        builder = GraphBuilder()
        stats = builder.build_graph()
        
        self.last_graph = {
            "timestamp": datetime.now().isoformat(),
            "nodes": stats.get("nodes", 0),
            "edges": stats.get("edges", 0),
        }
        logger.info(f"🕸️ Graph: {stats.get('nodes', 0)} nodes, {stats.get('edges', 0)} edges")
    
    def get_status(self) -> dict:
        """Get status of all rituals."""
        return {
            "running": self.running,
            "last_heartbeat": self.last_heartbeat,
            "last_suture": self.last_suture or {},
            "last_graph": self.last_graph or {},
            "last_hmem": self.last_hmem or {},
            "last_graphify": self.last_graphify or {},
        }


class BraveCounter:
    """Brave Search API counter."""
    
    def __init__(self):
        self.limit = config.BRAVE_MONTHLY_LIMIT
        self._load()
    
    def _load(self):
        """Load counter from file."""
        if config.BRAVE_COUNTER_FILE.exists():
            try:
                data = json.loads(config.BRAVE_COUNTER_FILE.read_text())
                self.count = data.get("count", 0)
                self.month = data.get("month", datetime.now().month)
            except:
                self.count = 0
                self.month = datetime.now().month
        else:
            self.count = 0
            self.month = datetime.now().month
    
    def _save(self):
        """Save counter to file."""
        if datetime.now().month != self.month:
            self.count = 0
            self.month = datetime.now().month
        
        config.BRAVE_COUNTER_FILE.write_text(json.dumps({
            "count": self.count,
            "month": self.month,
        }, indent=2), encoding="utf-8")
    
    def can_search(self) -> bool:
        """Check if we can search."""
        self._load()
        return self.count < self.limit
    
    def increment(self):
        """Increment counter."""
        self.count += 1
        self._save()
    
    def get_left(self) -> int:
        """Get remaining searches."""
        self._load()
        return max(0, self.limit - self.count)


class MemorySkill:
    """Persistent memory for the agent."""
    
    def __init__(self):
        self.memory_file = config.STORAGE_DIR / "memory.json"
        self._load()
    
    def _load(self):
        """Load memory."""
        self.memories = []
        if self.memory_file.exists():
            try:
                self.memories = json.loads(self.memory_file.read_text())
            except:
                self.memories = []
    
    def _save(self):
        """Save memory."""
        config.STORAGE_DIR.mkdir(exist_ok=True)
        self.memory_file.write_text(json.dumps(self.memories[-100:], indent=2), encoding="utf-8")
    
    def add(self, memory: str, category: str = "general"):
        """Add a memory."""
        self.memories.append({
            "content": memory,
            "category": category,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()
    
    def get_recent(self, limit: int = 10) -> list:
        """Get recent memories."""
        return self.memories[-limit:]
    
    def search(self, query: str) -> list:
        """Search memories."""
        return [m for m in self.memories if query.lower() in m.get("content", "").lower()]


class WikiHealer:
    """Heals orphaned wiki notes."""
    
    def heal_orphans(self) -> int:
        """Find and heal orphaned notes."""
        if not config.WIKI_DIR.exists():
            return 0
        
        healed = 0
        
        for md_file in config.WIKI_DIR.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if "relacionados:" in content or "relations:" in content:
                    continue
                
                if "estado: draft" in content or "estado: final" in content:
                    healed += 1
            except:
                pass
        
        return healed


class AgentState:
    """Tracks agent alive/failed state persistently."""
    
    def __init__(self):
        self._load()
    
    def _load(self):
        """Load state from file."""
        if config.AGENT_STATE_FILE.exists():
            try:
                self.state = json.loads(config.AGENT_STATE_FILE.read_text())
            except:
                self.state = self._default()
        else:
            self.state = self._default()
    
    def _default(self) -> dict:
        return {
            "alive": False,
            "last_alive": None,
            "last_failure": None,
            "failure_count": 0,
            "success_count": 0,
            "uptime_start": None,
            "failures": [],
        }
    
    def _save(self):
        """Save state to file."""
        config.AGENT_STATE_FILE.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
    
    def mark_alive(self):
        """Mark agent as alive."""
        now = datetime.now().isoformat()
        self.state["alive"] = True
        self.state["last_alive"] = now
        if not self.state.get("uptime_start"):
            self.state["uptime_start"] = now
        self._save()
    
    def mark_dead(self):
        """Mark agent as dead."""
        self.state["alive"] = False
        self.state["uptime_start"] = None
        self._save()
    
    def record_failure(self, error: str):
        """Record a failure."""
        now = datetime.now().isoformat()
        self.state["last_failure"] = now
        self.state["failure_count"] += 1
        self.state["failure_count_last"] = self.state.get("failure_count", 0)
        self.state["failures"].append({
            "error": error,
            "time": now,
        })
        self.state["failures"] = self.state["failures"][-20:]
        self._save()
    
    def record_success(self):
        """Record a success."""
        self.state["success_count"] += 1
    
    def get_status(self) -> dict:
        """Get current status."""
        self._load()
        return {
            "alive": self.state.get("alive", False),
            "last_alive": self.state.get("last_alive"),
            "last_failure": self.state.get("last_failure"),
            "failure_count": self.state.get("failure_count", 0),
            "success_count": self.state.get("success_count", 0),
            "uptime_start": self.state.get("uptime_start"),
            "recent_failures": self.state.get("failures", [])[-5:],
        }


class GraphBuilder:
    """Builds knowledge graph."""
    
    def build_graph(self) -> dict:
        """Build graph from wiki."""
        nodes = set()
        edges = []
        
        if not config.WIKI_DIR.exists():
            return {"nodes": 0, "edges": 0}
        
        for md_file in config.WIKI_DIR.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                
                for line in content.split("\n"):
                    if "[[" in line and "]]" in line:
                        nodes.add(md_file.stem)
                        
                        from re import findall
                        links = findall(r"\[\[(.+?)\]\]", line)
                        for link in links:
                            edges.append((md_file.stem, link))
                            nodes.add(link)
            except:
                pass
        
        return {"nodes": len(nodes), "edges": len(edges)}