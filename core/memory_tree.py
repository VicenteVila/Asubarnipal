"""H-Mem Memory Tree - Temporal-semantic hierarchical memory."""

import json
import logging
import math
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


class MemoryTree:
    """
    Temporal-semantic tree for H-Mem.
    
    Levels:
    - L0 (leaf): Original memory fragments (1 day window)
    - L1: Daily consolidations (7 day window)
    - L2: Weekly consolidations (30 day window)  
    - L3 (root): Monthly consolidations (summary)
    
    Features:
    - Incremental insertion with temporal-semantic consolidation
    - Ebbinghaus-based memory robustness scoring
    - Bottom-up retrieval by time scope
    """
    
    DEFAULT_LEVELS = {
        0: {"alpha": 0.75, "beta_days": 1, "name": "events"},
        1: {"alpha": 0.65, "beta_days": 7, "name": "daily"},
        2: {"alpha": 0.55, "beta_days": 30, "name": "weekly"},
        3: {"alpha": 0.50, "beta_days": 90, "name": "monthly"},
    }
    
    # Ebbinghaus parameters
    TAU = 30.0
    ETA = 0.5
    
    def __init__(self, vault_name: Optional[str] = None, levels: dict = None):
        self.vault_name = vault_name or self._get_active_vault_name()
        self.levels_config = levels or self.DEFAULT_LEVELS.copy()
        self.db_path = self._get_db_path()
        self.llm_router = None
        self.embeddings_model = None
        self._init_db()
    
    def _get_active_vault_name(self) -> Optional[str]:
        try:
            from core.vault_manager import get_vault_manager
            active = get_vault_manager().get_active()
            if active:
                return active.get("name")
        except Exception:
            pass
        return None
    
    def _get_db_path(self) -> Path:
        if self.vault_name:
            safe_name = self.vault_name.replace(" ", "_").lower()
            return config.DATA_DIR / f"memory_tree_{safe_name}.db"
        return config.DATA_DIR / "memory_tree.db"
    
    def _init_db(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT UNIQUE NOT NULL,
                level INTEGER NOT NULL,
                content TEXT,
                summary TEXT,
                parent_id TEXT,
                children_ids TEXT DEFAULT '[]',
                timestamp TEXT NOT NULL,
                time_window_start TEXT,
                time_window_end TEXT,
                consolidation_count INTEGER DEFAULT 0,
                last_consolidation TEXT,
                embedding_id INTEGER,
                node_type TEXT DEFAULT 'event',
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                embedding BLOB NOT NULL,
                model_name TEXT,
                created_at TEXT
            )
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_level ON memory_nodes(level)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_nodes(timestamp)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_time_window ON memory_nodes(time_window_start, time_window_end)
        """)
        
        self.conn.commit()
        logger.info(f"MemoryTree initialized at {self.db_path}")
    
    def _get_llm(self):
        if self.llm_router is None:
            from core.llm_router import LLMRouter
            self.llm_router = LLMRouter()
        return self.llm_router
    
    def _get_embeddings_model(self):
        if self.embeddings_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                model_name = config.RAG_MODEL
                self.embeddings_model = SentenceTransformer(model_name, device=config.RAG_DEVICE)
                logger.info(f"Embeddings model loaded: {model_name}")
            except Exception as e:
                logger.warning(f"Could not load embeddings model: {e}")
        return self.embeddings_model
    
    def _generate_node_id(self, level: int, timestamp: str) -> str:
        return f"node_{level}_{timestamp}_{int(time.time() * 1000) % 1000000}"
    
    def _get_time_window(self, timestamp: str, level: int) -> tuple:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00").replace("+00:00", ""))
        if "+" in timestamp:
            dt = datetime.fromisoformat(timestamp.split("+")[0])
        
        beta = self.levels_config.get(level, {}).get("beta_days", 1)
        
        window_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(days=beta)
        
        return window_start.isoformat(), window_end.isoformat()
    
    def _compute_similarity(self, content1: str, content2: str) -> float:
        model = self._get_embeddings_model()
        if model is None:
            return 0.5
        
        try:
            embeddings = model.encode([content1, content2])
            emb1, emb2 = embeddings[0], embeddings[1]
            
            dot = sum(a * b for a, b in zip(emb1, emb2))
            norm1 = math.sqrt(sum(a * a for a in emb1))
            norm2 = math.sqrt(sum(a * a for a in emb2))
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot / (norm1 * norm2)
        except Exception as e:
            logger.warning(f"Similarity computation failed: {e}")
            return 0.5
    
    def _generate_summary(self, contents: list[str]) -> str:
        if len(contents) == 1:
            return contents[0][:500]
        
        llm = self._get_llm()
        combined = "\n---\n".join(contents[:10])
        
        prompt = f"""Resume los siguientes fragmentos de memoria en 2-3 oraciones concisas:
        
{combined[:4000]}

RESUMEN:"""
        
        try:
            summary = llm.generate(prompt)
            return summary[:500] if summary else contents[0][:500]
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return contents[0][:500]
    
    def _memory_robustness(self, node: dict, query_time: datetime = None) -> float:
        if query_time is None:
            query_time = datetime.now()
        
        last_cons = node.get("last_consolidation") or node.get("timestamp")
        if not last_cons:
            return 1.0
        
        try:
            if "+" in last_cons:
                last_cons = last_cons.split("+")[0]
            r_m = datetime.fromisoformat(last_cons)
        except Exception:
            r_m = datetime.now()
        
        n_m = node.get("consolidation_count", 0)
        
        dt = (query_time - r_m).total_seconds() / 86400
        
        tau = self.TAU
        eta = self.ETA
        
        robustness = math.exp(-dt / (tau * (1 + eta * math.log(1 + n_m))))
        
        return max(0.0, min(1.0, robustness))
    
    def insert(
        self,
        content: str,
        timestamp: str = None,
        metadata: dict = None
    ) -> dict:
        """Insert a memory fragment into the tree."""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        node_id = self._generate_node_id(0, timestamp)
        window_start, window_end = self._get_time_window(timestamp, 0)
        
        node = {
            "node_id": node_id,
            "level": 0,
            "content": content,
            "summary": None,
            "parent_id": None,
            "children_ids": "[]",
            "timestamp": timestamp,
            "time_window_start": window_start,
            "time_window_end": window_end,
            "consolidation_count": 0,
            "last_consolidation": timestamp,
            "node_type": "event",
            "metadata": json.dumps(metadata or {}),
        }
        
        self.cursor.execute("""
            INSERT INTO memory_nodes 
            (node_id, level, content, summary, parent_id, children_ids, timestamp,
             time_window_start, time_window_end, consolidation_count, last_consolidation, node_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node["node_id"], node["level"], node["content"], node["summary"],
            node["parent_id"], node["children_ids"], node["timestamp"],
            node["time_window_start"], node["time_window_end"], node["consolidation_count"],
            node["last_consolidation"], node["node_type"], node["metadata"]
        ))
        
        self.conn.commit()
        
        self._propagate_consolidation(node_id, level=0)
        
        logger.info(f"Inserted memory node: {node_id[:20]}...")
        return node
    
    def _propagate_consolidation(self, node_id: str, level: int):
        """Propagate consolidation up the tree."""
        if level >= max(self.levels_config.keys()):
            return
        
        self.cursor.execute(
            "SELECT * FROM memory_nodes WHERE node_id = ?",
            (node_id,)
        )
        current = dict(self.cursor.fetchone())
        
        if current is None:
            return
        
        current_level = current["level"]
        alpha = self.levels_config.get(current_level, {}).get("alpha", 0.7)
        
        if current_level < level:
            return
        
        next_level = current_level + 1
        window_start, window_end = self._get_time_window(current["timestamp"], next_level)
        
        self.cursor.execute("""
            SELECT * FROM memory_nodes 
            WHERE level = ? 
            AND time_window_start = ? 
            AND time_window_end = ?
        """, (next_level, window_start, window_end))
        
        candidates = [dict(row) for row in self.cursor.fetchall()]
        
        similar_node = None
        max_sim = alpha
        
        for candidate in candidates:
            if candidate["node_id"] == node_id:
                continue
            
            sim = self._compute_similarity(
                current.get("summary") or current.get("content", "")[:500],
                candidate.get("summary") or candidate.get("content", "")[:500]
            )
            
            if sim > max_sim:
                max_sim = sim
                similar_node = candidate
        
        if similar_node:
            self._merge_nodes(similar_node["node_id"], node_id, next_level)
        else:
            self._create_parent_node(node_id, next_level, window_start, window_end)
    
    def _merge_nodes(self, parent_node_id: str, child_node_id: str, level: int):
        """Merge a child node into an existing parent."""
        self.cursor.execute("SELECT * FROM memory_nodes WHERE node_id = ?", (parent_node_id,))
        parent = dict(self.cursor.fetchone())
        
        self.cursor.execute("SELECT * FROM memory_nodes WHERE node_id = ?", (child_node_id,))
        child = dict(self.cursor.fetchone())
        
        if parent is None or child is None:
            return
        
        children = json.loads(parent["children_ids"])
        if child_node_id not in children:
            children.append(child_node_id)
        
        contents = []
        if parent.get("content"):
            contents.append(parent["content"])
        if parent.get("summary"):
            contents.append(parent["summary"])
        if child.get("content"):
            contents.append(child["content"])
        if child.get("summary"):
            contents.append(child["summary"])
        
        new_summary = self._generate_summary(contents)
        
        now = datetime.now().isoformat()
        new_count = parent.get("consolidation_count", 0) + 1
        
        self.cursor.execute("""
            UPDATE memory_nodes 
            SET children_ids = ?, summary = ?, consolidation_count = ?, last_consolidation = ?
            WHERE node_id = ?
        """, (json.dumps(children), new_summary, new_count, now, parent_node_id))
        
        self.cursor.execute("""
            UPDATE memory_nodes 
            SET parent_id = ?
            WHERE node_id = ?
        """, (parent_node_id, child_node_id))
        
        self.conn.commit()
        
        logger.info(f"Merged node {child_node_id[:15]} into parent {parent_node_id[:15]}")
        
        self._propagate_consolidation(parent_node_id, level + 1)
    
    def _create_parent_node(self, child_node_id: str, level: int, window_start: str, window_end: str):
        """Create a new parent node at the given level."""
        self.cursor.execute("SELECT * FROM memory_nodes WHERE node_id = ?", (child_node_id,))
        child = dict(self.cursor.fetchone())
        
        if child is None:
            return
        
        node_id = self._generate_node_id(level, window_start)
        
        parent = {
            "node_id": node_id,
            "level": level,
            "content": child.get("summary") or child.get("content"),
            "summary": None,
            "parent_id": None,
            "children_ids": json.dumps([child_node_id]),
            "timestamp": window_start,
            "time_window_start": window_start,
            "time_window_end": window_end,
            "consolidation_count": 1,
            "last_consolidation": datetime.now().isoformat(),
            "node_type": "consolidation",
            "metadata": "{}",
        }
        
        self.cursor.execute("""
            INSERT INTO memory_nodes 
            (node_id, level, content, summary, parent_id, children_ids, timestamp,
             time_window_start, time_window_end, consolidation_count, last_consolidation, node_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            parent["node_id"], parent["level"], parent["content"], parent["summary"],
            parent["parent_id"], parent["children_ids"], parent["timestamp"],
            parent["time_window_start"], parent["time_window_end"], parent["consolidation_count"],
            parent["last_consolidation"], parent["node_type"], parent["metadata"]
        ))
        
        self.cursor.execute("""
            UPDATE memory_nodes SET parent_id = ? WHERE node_id = ?
        """, (node_id, child_node_id))
        
        self.conn.commit()
        
        logger.info(f"Created parent node at level {level}: {node_id[:15]}")
        
        self._propagate_consolidation(node_id, level + 1)
    
    def query(
        self,
        query: str,
        time_range: tuple = None,
        scope: str = "mixed",
        limit: int = 10
    ) -> list[dict]:
        """
        Query the tree for relevant memory evidence.
        
        Args:
            query: Search query
            time_range: (start, end) tuple for temporal filtering
            scope: "short", "long", or "mixed"
            limit: Maximum results
            
        Returns:
            List of memory nodes with scores
        """
        results = []
        now = datetime.now()
        
        if scope in ["short", "mixed"]:
            results.extend(self._query_level(query, 0, time_range, limit // 2, now))
            results.extend(self._query_level(query, 1, time_range, limit // 2, now))
        
        if scope in ["long", "mixed"]:
            results.extend(self._query_level(query, 2, time_range, limit // 2, now))
            results.extend(self._query_level(query, 3, time_range, limit // 2, now))
        
        results = self._rank_results(results, query, now)
        
        return results[:limit]
    
    def _query_level(self, query: str, level: int, time_range: tuple, limit: int, query_time: datetime) -> list[dict]:
        """Query a specific level of the tree."""
        if time_range:
            start, end = time_range
            where_clause = "WHERE level = ? AND time_window_start >= ? AND time_window_end <= ?"
            params = [level, start, end]
        else:
            where_clause = "WHERE level = ?"
            params = [level]
        
        self.cursor.execute(f"""
            SELECT * FROM memory_nodes {where_clause} ORDER BY timestamp DESC LIMIT ?
        """, (*params, limit * 2))
        
        nodes = [dict(row) for row in self.cursor.fetchall()]
        
        scored = []
        for node in nodes:
            sim = self._compute_similarity(
                query,
                node.get("summary") or node.get("content", "")[:500]
            )
            
            if time_range:
                temp_relevance = self._temporal_relevance(node, time_range)
            else:
                temp_relevance = 0.5
            
            robustness = self._memory_robustness(node, query_time)
            
            total_score = 0.5 * sim + 0.3 * temp_relevance + 0.2 * robustness
            
            scored.append({
                "node": node,
                "score": total_score,
                "semantic_sim": sim,
                "temporal_relevance": temp_relevance,
                "robustness": robustness,
            })
        
        return scored
    
    def _temporal_relevance(self, node: dict, time_range: tuple) -> float:
        """Calculate temporal relevance based on overlap and distance."""
        node_start = node.get("time_window_start", "")
        node_end = node.get("time_window_end", "")
        
        if not node_start or not node_end:
            return 0.5
        
        try:
            if "+" in node_start:
                node_start = node_start.split("+")[0]
            if "+" in node_end:
                node_end = node_end.split("+")[0]
            
            ns = datetime.fromisoformat(node_start)
            ne = datetime.fromisoformat(node_end)
            
            query_start = datetime.fromisoformat(time_range[0])
            query_end = datetime.fromisoformat(time_range[1])
            
            overlap_start = max(ns, query_start)
            overlap_end = min(ne, query_end)
            overlap = max(0, (overlap_end - overlap_start).total_seconds())
            
            union = max(ne, query_end) - min(ns, query_start)
            union_sec = max(1, union.total_seconds())
            
            overlap_ratio = overlap / union_sec
            
            node_center = ns + (ne - ns) / 2
            query_center = query_start + (query_end - query_start) / 2
            center_dist = abs((node_center - query_center).total_seconds())
            
            dist_ratio = 1 - min(1.0, center_dist / union_sec)
            
            return 0.6 * overlap_ratio + 0.4 * dist_ratio
            
        except Exception as e:
            logger.warning(f"Temporal relevance calculation failed: {e}")
            return 0.5
    
    def _rank_results(self, results: list[dict], query: str, query_time: datetime) -> list[dict]:
        """Rank results by combined score."""
        seen_ids = set()
        unique = []
        
        for r in results:
            node_id = r["node"]["node_id"]
            if node_id not in seen_ids:
                seen_ids.add(node_id)
                unique.append(r)
        
        return sorted(unique, key=lambda x: x["score"], reverse=True)
    
    def get_stats(self) -> dict:
        """Get tree statistics."""
        self.cursor.execute("SELECT COUNT(*) as total FROM memory_nodes")
        total = self.cursor.fetchone()[0]
        
        stats = {"total_nodes": total, "by_level": {}}
        
        for level in self.levels_config.keys():
            self.cursor.execute("SELECT COUNT(*) FROM memory_nodes WHERE level = ?", (level,))
            count = self.cursor.fetchone()[0]
            stats["by_level"][f"L{level}_{self.levels_config[level]['name']}"] = count
        
        self.cursor.execute("SELECT MAX(timestamp) FROM memory_nodes")
        last = self.cursor.fetchone()[0]
        stats["last_insert"] = last
        
        return stats
    
    def get_recent(self, limit: int = 20, level: int = None) -> list[dict]:
        """Get recent nodes, optionally filtered by level."""
        if level is not None:
            self.cursor.execute("""
                SELECT * FROM memory_nodes WHERE level = ? 
                ORDER BY timestamp DESC LIMIT ?
            """, (level, limit))
        else:
            self.cursor.execute("""
                SELECT * FROM memory_nodes ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def force_consolidation(self) -> dict:
        """Force consolidation of all nodes that need it."""
        now = datetime.now().isoformat()
        
        for level in range(3):
            beta = self.levels_config.get(level, {}).get("beta_days", 1)
            
            self.cursor.execute("""
                SELECT * FROM memory_nodes 
                WHERE level = ? AND consolidation_count = 0
            """, (level,))
            
            nodes = [dict(row) for row in self.cursor.fetchall()]
            
            for node in nodes:
                self._propagate_consolidation(node["node_id"], level)
        
        return {"status": "consolidation_forced", "timestamp": now}
    
    def prune_old_nodes(self, days: int = 90) -> int:
        """Prune nodes older than specified days (keeping summaries)."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        self.cursor.execute("""
            DELETE FROM memory_nodes 
            WHERE level < 2 AND timestamp < ?
        """, (cutoff,))
        
        deleted = self.cursor.rowcount
        
        self.conn.commit()
        
        logger.info(f"Pruned {deleted} old nodes")
        return deleted
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def get_memory_tree(vault_name: str = None) -> MemoryTree:
    return MemoryTree(vault_name=vault_name)