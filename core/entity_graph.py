"""H-Mem Entity Graph - Entity-centered knowledge graph for multi-hop reasoning."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


class EntityGraph:
    """
    Knowledge graph for entity-centered memory.
    
    Features:
    - Entity extraction from memory fragments
    - Multi-hop traversal for reasoning
    - Entity profiles with persistent information
    - Temporal relationships
    """
    
    ENTITY_TYPES = [
        "person", "organization", "location", "concept", 
        "event", "topic", "preference", "task", "project"
    ]
    
    RELATION_TYPES = [
        "related_to", "part_of", "works_on", "located_at", 
        "created_by", "mentioned_in", "references", "depends_on"
    ]
    
    def __init__(self, vault_name: Optional[str] = None):
        self.vault_name = vault_name or self._get_active_vault_name()
        self.db_path = self._get_db_path()
        self.llm_router = None
        self._init_db()
    
    def _get_active_vault_name(self) -> Optional[str]:
        try:
            from core.vault_manager import get_vault_manager
            active = get_vault_manager().get_active()
            if active:
                return active.get("name")
        except:
            pass
        return None
    
    def _get_db_path(self) -> Path:
        if self.vault_name:
            safe_name = self.vault_name.replace(" ", "_").lower()
            return config.DATA_DIR / f"entity_graph_{safe_name}.db"
        return config.DATA_DIR / "entity_graph.db"
    
    def _init_db(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                entity_type TEXT DEFAULT 'concept',
                profile TEXT,
                salience_score REAL DEFAULT 0.0,
                first_seen TEXT,
                last_updated TEXT,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relation_id TEXT UNIQUE NOT NULL,
                from_entity TEXT NOT NULL,
                to_entity TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                bidireccional INTEGER DEFAULT 0,
                temporal_start TEXT,
                temporal_end TEXT,
                context TEXT,
                created_at TEXT,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_memory_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                memory_source TEXT,
                memory_type TEXT,
                memory_content TEXT,
                linked_at TEXT,
                relevance_score REAL DEFAULT 1.0
            )
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(name)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_from_entity ON relations(from_entity)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_to_entity ON relations(to_entity)
        """)
        
        self.conn.commit()
        logger.info(f"EntityGraph initialized at {self.db_path}")
    
    def _get_llm(self):
        if self.llm_router is None:
            from core.llm_router import LLMRouter
            self.llm_router = LLMRouter()
        return self.llm_router
    
    def _generate_entity_id(self, name: str) -> str:
        safe = name.lower().replace(" ", "_").replace(",", "")[:50]
        return f"ent_{safe}_{int(datetime.now().timestamp() * 1000) % 100000}"
    
    def _generate_relation_id(self, from_ent: str, to_ent: str, rel_type: str) -> str:
        return f"rel_{from_ent[:20]}_{to_ent[:20]}_{rel_type}"[:80]
    
    def add_entity(
        self,
        name: str,
        entity_type: str = "concept",
        profile: str = None,
        metadata: dict = None
    ) -> dict:
        """Add or update an entity."""
        entity_id = self._generate_entity_id(name)
        now = datetime.now().isoformat()
        
        existing = self.get_entity(name)
        if existing:
            return self.update_entity(existing["entity_id"], profile=profile, metadata=metadata)
        
        entity = {
            "entity_id": entity_id,
            "name": name,
            "entity_type": entity_type,
            "profile": profile or "",
            "salience_score": 1.0,
            "first_seen": now,
            "last_updated": now,
            "metadata": json.dumps(metadata or {}),
        }
        
        self.cursor.execute("""
            INSERT INTO entities 
            (entity_id, name, entity_type, profile, salience_score, first_seen, last_updated, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity["entity_id"], entity["name"], entity["entity_type"],
            entity["profile"], entity["salience_score"], entity["first_seen"],
            entity["last_updated"], entity["metadata"]
        ))
        
        self.conn.commit()
        
        logger.info(f"Added entity: {name} ({entity_type})")
        return entity
    
    def update_entity(
        self,
        entity_id: str,
        profile: str = None,
        salience_delta: float = 0.0,
        metadata: dict = None
    ) -> bool:
        """Update an existing entity."""
        now = datetime.now().isoformat()
        
        if profile is not None:
            self.cursor.execute("UPDATE entities SET profile = ?, last_updated = ? WHERE entity_id = ?",
                             (profile, now, entity_id))
        
        if salience_delta != 0:
            self.cursor.execute("""
                UPDATE entities SET salience_score = salience_score + ?, last_updated = ? 
                WHERE entity_id = ?
            """, (salience_delta, now, entity_id))
        
        if metadata:
            self.cursor.execute("SELECT metadata FROM entities WHERE entity_id = ?", (entity_id,))
            row = self.cursor.fetchone()
            if row:
                existing = json.loads(row[0] or "{}")
                existing.update(metadata)
                self.cursor.execute("UPDATE entities SET metadata = ?, last_updated = ? WHERE entity_id = ?",
                                 (json.dumps(existing), now, entity_id))
        
        self.conn.commit()
        return True
    
    def get_entity(self, name: str) -> Optional[dict]:
        """Get entity by name."""
        self.cursor.execute("SELECT * FROM entities WHERE LOWER(name) = LOWER(?)", (name,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_entities_by_type(self, entity_type: str, limit: int = 100) -> list[dict]:
        """Get all entities of a specific type."""
        self.cursor.execute("""
            SELECT * FROM entities WHERE entity_type = ? 
            ORDER BY salience_score DESC LIMIT ?
        """, (entity_type, limit))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def add_relation(
        self,
        from_entity: str,
        to_entity: str,
        relation_type: str = "related_to",
        weight: float = 1.0,
        context: str = None,
        bidireccional: bool = False
    ) -> dict:
        """Add a relation between two entities."""
        relation_id = self._generate_relation_id(from_entity, to_entity, relation_type)
        now = datetime.now().isoformat()
        
        from_ent = self.get_entity(from_entity)
        to_ent = self.get_entity(to_entity)
        
        if not from_ent:
            from_ent = self.add_entity(from_entity, "concept")
        if not to_ent:
            to_ent = self.add_entity(to_entity, "concept")
        
        existing = self.cursor.execute("""
            SELECT * FROM relations WHERE from_entity = ? AND to_entity = ?
        """, (from_ent["entity_id"], to_ent["entity_id"])).fetchone()
        
        if existing:
            self.cursor.execute("""
                UPDATE relations SET weight = ?, context = ? WHERE id = ?
            """, (weight, context, existing[0]))
            self.conn.commit()
            return dict(existing)
        
        relation = {
            "relation_id": relation_id,
            "from_entity": from_ent["entity_id"],
            "to_entity": to_ent["entity_id"],
            "relation_type": relation_type,
            "weight": weight,
            "bidireccional": 1 if bidireccional else 0,
            "temporal_start": now,
            "temporal_end": None,
            "context": context,
            "created_at": now,
            "metadata": "{}",
        }
        
        self.cursor.execute("""
            INSERT INTO relations 
            (relation_id, from_entity, to_entity, relation_type, weight, bidireccional,
             temporal_start, temporal_end, context, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            relation["relation_id"], relation["from_entity"], relation["to_entity"],
            relation["relation_type"], relation["weight"], relation["bidireccional"],
            relation["temporal_start"], relation["temporal_end"], relation["context"],
            relation["created_at"], relation["metadata"]
        ))
        
        self.conn.commit()
        
        self.update_entity(from_ent["entity_id"], salience_delta=0.1)
        self.update_entity(to_ent["entity_id"], salience_delta=0.1)
        
        logger.info(f"Added relation: {from_entity} --[{relation_type}]--> {to_entity}")
        return relation
    
    def expand(
        self,
        seed_entities: list[str],
        hops: int = 2,
        relation_types: list[str] = None
    ) -> list[dict]:
        """
        Expand from seed entities to find related entities (multi-hop).
        
        Args:
            seed_entities: List of entity names to start from
            hops: Number of hops to traverse (1-3)
            relation_types: Filter by specific relation types
            
        Returns:
            List of expanded entities with paths
        """
        expanded = []
        visited = set()
        frontier = []
        
        for name in seed_entities:
            ent = self.get_entity(name)
            if ent:
                frontier.append({"entity": ent, "path": [], "depth": 0})
        
        while frontier:
            current = frontier.pop(0)
            ent = current["entity"]
            
            if ent["entity_id"] in visited:
                continue
            
            visited.add(ent["entity_id"])
            
            if current["depth"] > 0:
                expanded.append({
                    "entity": ent,
                    "path": current["path"],
                    "depth": current["depth"],
                })
            
            if current["depth"] >= hops:
                continue
            
            relations = self.get_relations(ent["entity_id"])
            
            for rel in relations:
                if relation_types and rel["relation_type"] not in relation_types:
                    continue
                
                target_id = rel["to_entity"]
                if target_id == ent["entity_id"]:
                    target_id = rel["from_entity"]
                
                target = self.get_entity_by_id(target_id)
                if target and target["entity_id"] not in visited:
                    new_path = current["path"] + [{
                        "type": rel["relation_type"],
                        "via": ent["name"],
                    }]
                    frontier.append({
                        "entity": target,
                        "path": new_path,
                        "depth": current["depth"] + 1,
                    })
        
        return expanded
    
    def get_relations(self, entity_id: str, as_source: bool = True) -> list[dict]:
        """Get all relations for an entity."""
        if as_source:
            self.cursor.execute("SELECT * FROM relations WHERE from_entity = ?", (entity_id,))
        else:
            self.cursor.execute("""
                SELECT * FROM relations WHERE from_entity = ? OR to_entity = ?
            """, (entity_id, entity_id))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_entity_by_id(self, entity_id: str) -> Optional[dict]:
        """Get entity by ID."""
        self.cursor.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def link_memory(
        self,
        entity_name: str,
        memory_source: str,
        memory_type: str,
        memory_content: str = None,
        relevance: float = 1.0
    ) -> dict:
        """Link a memory fragment to an entity."""
        ent = self.get_entity(entity_name)
        if not ent:
            ent = self.add_entity(entity_name)
        
        now = datetime.now().isoformat()
        
        link = {
            "entity_id": ent["entity_id"],
            "memory_source": memory_source,
            "memory_type": memory_type,
            "memory_content": memory_content or "",
            "linked_at": now,
            "relevance_score": relevance,
        }
        
        self.cursor.execute("""
            INSERT INTO entity_memory_links 
            (entity_id, memory_source, memory_type, memory_content, linked_at, relevance_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            link["entity_id"], link["memory_source"], link["memory_type"],
            link["memory_content"], link["linked_at"], link["relevance_score"]
        ))
        
        self.conn.commit()
        
        self.update_entity(ent["entity_id"], salience_delta=0.05)
        
        return link
    
    def extract_entities(self, text: str, max_entities: int = 10) -> list[dict]:
        """
        Extract entities from text using LLM.
        
        Returns list of (name, type) tuples.
        """
        llm = self._get_llm()
        
        prompt = f"""Extrae las entidades importantes del siguiente texto.
Devuelve una lista de máximo {max_entities} entidades en formato JSON:
[
  {{"name": "nombre_entidad", "type": "person|organization|location|concept|event"}},
  ...
]

Texto:
{text[:3000]}

Solo devuelve el JSON, sin explicaciones:"""
        
        try:
            result = llm.generate(prompt)
            
            result = result.strip()
            if result.startswith("```"):
                lines = result.split("\n")[1:]
                result = "\n".join(lines)
                if result.endswith("```"):
                    result = result[:-3]
            
            entities = json.loads(result)
            
            valid_types = self.ENTITY_TYPES
            filtered = [
                e for e in entities 
                if isinstance(e, dict) and e.get("type") in valid_types
            ]
            
            return filtered[:max_entities]
            
        except json.JSONDecodeError as e:
            logger.warning(f"Entity extraction JSON parse failed: {e}")
            return []
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            return []
    
    def ingest_with_entities(
        self,
        content: str,
        source: str,
        content_type: str = "memory"
    ) -> dict:
        """Ingest content and automatically extract/create entities and relations."""
        entities = self.extract_entities(content)
        
        added_entities = []
        for ent_data in entities:
            ent = self.add_entity(
                name=ent_data["name"],
                entity_type=ent_data.get("type", "concept"),
                metadata={"source": source, "content_type": content_type}
            )
            added_entities.append(ent["name"])
            
            self.link_memory(
                entity_name=ent["name"],
                memory_source=source,
                memory_type=content_type,
                memory_content=content[:500]
            )
        
        for i, ent1 in enumerate(added_entities):
            for ent2 in added_entities[i+1:]:
                self.add_relation(
                    from_entity=ent1,
                    to_entity=ent2,
                    relation_type="mentioned_together",
                    context=f"From {source}"
                )
        
        return {
            "entities_added": len(added_entities),
            "entities": added_entities,
            "source": source,
        }
    
    def get_neighbors(self, entity_name: str, limit: int = 10) -> list[dict]:
        """Get direct neighbors of an entity."""
        ent = self.get_entity(entity_name)
        if not ent:
            return []
        
        relations = self.get_relations(ent["entity_id"])
        
        neighbors = []
        for rel in relations:
            target_id = rel["to_entity"] if rel["from_entity"] == ent["entity_id"] else rel["from_entity"]
            target = self.get_entity_by_id(target_id)
            
            if target:
                neighbors.append({
                    "entity": target,
                    "relation": rel["relation_type"],
                    "weight": rel["weight"],
                })
        
        return sorted(neighbors, key=lambda x: x["weight"], reverse=True)[:limit]
    
    def get_hubs(self, limit: int = 10) -> list[dict]:
        """Get most connected entities (hubs)."""
        self.cursor.execute("""
            SELECT e.entity_id, e.name, e.entity_type, e.salience_score,
                   COUNT(DISTINCT r.from_entity) + COUNT(DISTINCT r.to_entity) as connections
            FROM entities e
            LEFT JOIN relations r ON e.entity_id = r.from_entity OR e.entity_id = r.to_entity
            GROUP BY e.entity_id
            ORDER BY connections DESC, e.salience_score DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_stats(self) -> dict:
        """Get graph statistics."""
        self.cursor.execute("SELECT COUNT(*) FROM entities")
        total_entities = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM relations")
        total_relations = self.cursor.fetchone()[0]
        
        type_counts = {}
        for etype in self.ENTITY_TYPES:
            self.cursor.execute("SELECT COUNT(*) FROM entities WHERE entity_type = ?", (etype,))
            count = self.cursor.fetchone()[0]
            if count > 0:
                type_counts[etype] = count
        
        self.cursor.execute("""
            SELECT COUNT(*) FROM relations WHERE bidireccional = 1
        """)
        bidirectional = self.cursor.fetchone()[0]
        
        return {
            "total_entities": total_entities,
            "total_relations": total_relations,
            "bidirectional_relations": bidirectional,
            "by_type": type_counts,
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def get_entity_graph(vault_name: str = None) -> EntityGraph:
    return EntityGraph(vault_name=vault_name)