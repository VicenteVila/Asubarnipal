"""Wiki module for Asubarnipal V2."""

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


class Wiki:
    """Wiki database and file management."""
    
    def __init__(self, wiki_path: Optional[Path] = None):
        self.wiki_path = wiki_path or config.WIKI_DIR
        self.wiki_path.mkdir(exist_ok=True)
        self.db_path = config.WIKI_PATH
        
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                tipo TEXT,
                fuente TEXT,
                fecha_ingesta TEXT,
                fecha_actualizacion TEXT,
                estado TEXT,
                tags TEXT,
                relacionados TEXT,
                content TEXT
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity INTEGER,
                to_entity INTEGER,
                relation_type TEXT,
                FOREIGN KEY(from_entity) REFERENCES entities(id),
                FOREIGN KEY(to_entity) REFERENCES entities(id)
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_hash TEXT UNIQUE,
                original_name TEXT,
                content TEXT,
                ingested_at TEXT
            )
        """)
        
        self.conn.commit()
        logger.info(f"Wiki initialized at {self.db_path}")
    
    def add_entity(
        self,
        name: str,
        content: str,
        tipo: str = "entity",
        fuente: str = "N/A",
        estado: str = "draft",
        tags: list = None,
        relacionados: list = None
    ) -> dict:
        """Add or update an entity."""
        now = datetime.now().isoformat()
        tags_json = json.dumps(tags or [])
        relacionados_json = json.dumps(relacionados or [])
        
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO entities 
                (name, content, tipo, fuente, fecha_ingesta, fecha_actualizacion, estado, tags, relacionados)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, content, tipo, fuente, now, now, estado, tags_json, relacionados_json))
            self.conn.commit()
            
            if relacionados:
                self._update_relations(name, relacionados)
            
            return {"success": True, "name": name}
        except Exception as e:
            return {"error": str(e)}
    
    def _update_relations(self, entity_name: str, relacionados: list):
        """Update relations for an entity."""
        self.cursor.execute("SELECT id FROM entities WHERE name = ?", (entity_name,))
        row = self.cursor.fetchone()
        if not row:
            return
        
        entity_id = row[0]
        
        self.cursor.execute("DELETE FROM relations WHERE from_entity = ?", (entity_id,))
        
        for related in relacionados:
            related = related.strip("[]").strip()
            self.cursor.execute("SELECT id FROM entities WHERE name = ?", (related,))
            r = self.cursor.fetchone()
            if r:
                self.cursor.execute("""
                    INSERT INTO relations (from_entity, to_entity, relation_type)
                    VALUES (?, ?, ?)
                """, (entity_id, r[0], "related"))
        
        self.conn.commit()
    
    def search(self, query: str, limit: int = 20) -> list:
        """Search wiki."""
        self.cursor.execute("""
            SELECT name, tipo, content FROM entities 
            WHERE name LIKE ? OR content LIKE ?
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        
        return [{"name": r[0], "tipo": r[1], "content": r[2]} for r in self.cursor.fetchall()]
    
    def get_hubs(self, limit: int = 10) -> list:
        """Get most connected entities (hubs)."""
        self.cursor.execute("""
            SELECT e.name, COUNT(r.id) as connections
            FROM entities e
            LEFT JOIN relations r ON e.id = r.from_entity OR e.id = r.to_entity
            GROUP BY e.id
            ORDER BY connections DESC
            LIMIT ?
        """, (limit,))
        
        return [{"name": r[0], "connections": r[1]} for r in self.cursor.fetchall()]
    
    def get_clusters(self) -> list:
        """Get thematic clusters."""
        self.cursor.execute("""
            SELECT tags FROM entities WHERE tags != '[]'
        """)
        
        tag_counts = {}
        for row in self.cursor.fetchall():
            try:
                tags = json.loads(row[0])
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except:
                pass
        
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"tag": t[0], "count": t[1]} for t in sorted_tags[:20]]
    
    def lint(self) -> dict:
        """Health check for wiki."""
        issues = []
        
        self.cursor.execute("SELECT name, relacionados FROM entities")
        for row in self.cursor.fetchall():
            name, relacionados = row[0], row[1]
            if not relacionados or relacionados == "[]":
                issues.append({"type": "orphan", "name": name})
                continue
            
            try:
                rels = json.loads(relacionados)
                for rel in rels:
                    rel = rel.strip("[]")
                    self.cursor.execute("SELECT id FROM entities WHERE name = ?", (rel,))
                    if not self.cursor.fetchone():
                        issues.append({"type": "broken_link", "name": name, "link": rel})
            except:
                pass
        
        return {
            "total_entities": self.cursor.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
            "issues": issues,
            "health_score": max(0, 100 - len(issues) * 10)
        }
    
    def get_all(self, limit: int = 100) -> list:
        """Get all entities."""
        self.cursor.execute(f"SELECT name, tipo, content FROM entities LIMIT {limit}")
        return [{"name": r[0], "tipo": r[1], "preview": r[2][:200]} for r in self.cursor.fetchall()]
    
    def ingest_url(self, url: str) -> dict:
        """Ingest content from URL."""
        import requests
        from bs4 import BeautifulSoup
        
        try:
            resp = requests.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            title = soup.title.string if soup.title else url
            text = soup.get_text()[:20000]
            
            return self.add_entity(
                name=title,
                content=text,
                tipo="source",
                fuente=url,
                estado="final"
            )
        except Exception as e:
            return {"error": str(e)}
    
    def ingest_pdf(self, file_path: str) -> dict:
        """Ingest PDF file."""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
            
            name = Path(file_path).stem
            return self.add_entity(
                name=name,
                content=text[:20000],
                tipo="source",
                fuente=file_path,
                estado="final"
            )
        except Exception as e:
            return {"error": str(e)}
    
    def sync_obsidian(self, vault_path: str = None) -> dict:
        """Sync from Obsidian vault."""
        vault = Path(vault_path or config.OBSIDIAN_PATH)
        
        if not vault.exists():
            return {"error": f"Vault not found: {vault}"}
        
        imported = 0
        for md_file in vault.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                
                frontmatter = {}
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end > 0:
                        fm_text = content[3:end]
                        for line in fm_text.split("\n"):
                            if ":" in line:
                                key, val = line.split(":", 1)
                                frontmatter[key.strip()] = val.strip()
                
                self.add_entity(
                    name=md_file.stem,
                    content=content[:20000],
                    tipo=frontmatter.get("tipo", "entity"),
                    fuente=frontmatter.get("fuente", "obsidian"),
                    estado=frontmatter.get("estado", "final"),
                    tags=frontmatter.get("tags", "").split(","),
                )
                imported += 1
            except:
                pass
        
        return {"imported": imported}
    
    def close(self):
        """Close database connection."""
        self.conn.close()


class WikiReader:
    """Read-only wiki access."""
    
    def __init__(self):
        self.wiki_path = config.WIKI_PATH
        self.conn = None
    
    def _connect(self):
        if not self.conn:
            self.conn = sqlite3.connect(str(self.wiki_path))
            self.conn.row_factory = sqlite3.Row
    
    def search(self, query: str) -> list:
        self._connect()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT name, content FROM entities 
            WHERE name LIKE ? OR content LIKE ?
            LIMIT 20
        """, (f"%{query}%", f"%{query}%"))
        return [{"name": r[0], "content": r[1]} for r in cursor.fetchall()]
    
    def get_all(self, limit: int = 100) -> list:
        self._connect()
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT name, tipo, content FROM entities LIMIT {limit}")
        return [{"name": r[0], "tipo": r[1], "content": r[2][:500]} for r in cursor.fetchall()]