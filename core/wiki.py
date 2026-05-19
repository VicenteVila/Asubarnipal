"""Wiki module for Asubarnipal V2."""

import json
import logging
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


class Wiki:
    """Wiki database and file management."""

    def __init__(self, wiki_path: Optional[Path] = None, vault_name: Optional[str] = None):
        self.wiki_path = wiki_path or self._get_vault_path(vault_name)
        self.wiki_path.mkdir(exist_ok=True)

        if vault_name:
            self.db_path = self._get_vault_db_path(vault_name)
        else:
            active_vault = self._get_active_vault_info()
            if active_vault:
                self.db_path = Path(active_vault.get("db_path", config.WIKI_PATH))
            else:
                self.db_path = config.WIKI_PATH

        self._init_db()

    def _get_vault_path(self, vault_name: str = None) -> Path:
        """Get vault path from VaultManager or config."""
        try:
            from core.vault_manager import get_vault_manager
            vm = get_vault_manager()

            if vault_name:
                vaults = vm._config.get("vaults", {})
                if vault_name in vaults:
                    return Path(vaults[vault_name]["path"])

            active = vm.get_active()
            if active:
                return Path(active["path"])
        except:
            pass

        return config.WIKI_DIR

    def _get_vault_db_path(self, vault_name: str) -> Path:
        """Get database path for a specific vault."""
        safe_name = vault_name.replace(" ", "_").lower()
        return config.DATA_DIR / f"wiki_{safe_name}.db"

    def _get_active_vault_info(self) -> Optional[dict]:
        """Get active vault info from VaultManager."""
        try:
            from core.vault_manager import get_vault_manager
            return get_vault_manager().get_active()
        except:
            return None
    
    def _init_db(self):
        """Initialize SQLite database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        self._create_tables()
        
        existing_columns = [col[1] for col in self.cursor.execute("PRAGMA table_info(entities)")]
        
        new_columns = {
            "tipo": "TEXT DEFAULT 'entity'",
            "fuente": "TEXT",
            "fecha_ingesta": "TEXT",
            "fecha_actualizacion": "TEXT",
            "estado": "TEXT DEFAULT 'draft'",
            "tags": "TEXT DEFAULT '[]'",
            "relacionados": "TEXT DEFAULT '[]'",
            "content": "TEXT",
        }
        
        for col_name, col_def in new_columns.items():
            if col_name not in existing_columns:
                try:
                    self.cursor.execute(f"ALTER TABLE entities ADD COLUMN {col_name} {col_def}")
                    logger.info(f"Added column: {col_name}")
                except Exception as e:
                    logger.warning(f"Could not add column {col_name}: {e}")
        
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
    
    def _create_tables(self):
        """Create all necessary tables."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                content TEXT
            )
        """)
    
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
        return [{"name": r[0], "tipo": r[1], "preview": (r[2] or "")[:200]} for r in self.cursor.fetchall()]
    
    def ingest_url(self, url: str) -> dict:
        """Ingest content from URL (legacy simple version)."""
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

    def ingest_url_smart(self, url: str, translate_to: str = "es") -> dict:
        """
        Smart URL ingestion with:
        - Content extraction (removes nav, scripts, ads)
        - Language detection
        - Translation to target language
        - Summary generation via LLM
        - Key concepts extraction
        - Link generation to existing notes
        """
        import requests
        from bs4 import BeautifulSoup
        from core.live_activity import get_tracker

        activity = get_tracker()
        activity.ingest_start(url)
        logger.info(f"Smart ingest starting for: {url}")

        try:
            activity.ingest_step("Descargando", 10)
            resp = requests.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Asubarnipal/1.0)"
            })

            if not resp.ok:
                activity.ingest_complete(success=False, details=f"HTTP {resp.status_code}")
                return {"error": f"HTTP {resp.status_code}"}

            activity.ingest_step("Limpiando HTML", 20)
            soup = BeautifulSoup(resp.text, "html.parser")

            title = soup.title.string.strip() if soup.title else url

            for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                           "noscript", "iframe", "form", "button"]):
                tag.decompose()

            activity.ingest_step("Extrayendo texto", 30)
            main_content = soup.get_text(separator=" ", strip=True)
            main_content = re.sub(r'\s+', ' ', main_content)
            main_content = main_content[:30000]

            activity.ingest_step("Detectando idioma", 40)
            lang = self._detect_language(main_content)
            logger.info(f"Detected language: {lang}")

            translated_content = main_content
            was_translated = False
            if lang != translate_to:
                activity.ingest_step("Traduciendo", 50)
                translated_content, was_translated = self._translate_text(main_content, target=translate_to)
                if was_translated:
                    logger.info(f"Translated from {lang} to {translate_to}")

            activity.ingest_step("Generando resumen", 60)
            summary = self._generate_summary(translated_content[:8000])

            activity.ingest_step("Extrayendo conceptos", 70)
            concepts = self._extract_concepts(translated_content[:5000])

            activity.ingest_step("Buscando relacionados", 80)
            related = self._find_related_notes(concepts[:5])

            activity.ingest_step("Creando entidades", 85)
            concept_entities = []
            for concept in concepts[:8]:
                clean_concept = concept.strip()[:100]
                if clean_concept and len(clean_concept) > 2:
                    self.add_entity(
                        name=clean_concept,
                        content=f"Concepto extraído de: {title}",
                        tipo="concept",
                        fuente=url,
                        estado="final",
                        tags=["auto-generated", "from-ingest"]
                    )
                    concept_entities.append(clean_concept)
                    self.save_to_obsidian(
                        name=clean_concept,
                        content=f"Concepto extraído de: {title}",
                        tipo="concept",
                        fuente=url,
                        tags=["auto-generated", "from-ingest"]
                    )

            activity.ingest_step("Guardando fuente", 90)
            relacionados = []
            for rel in related:
                relacionados.append({"name": rel["name"], "relation": "related"})

            source = self.add_entity(
                name=title,
                content=translated_content[:30000],
                tipo="source",
                fuente=url,
                estado="final",
                tags=concepts[:10],
                relacionados=relacionados
            )
            
            activity.ingest_step("Guardando en Obsidian", 92)
            obsidian_result = self.save_to_obsidian(
                name=title,
                content=translated_content[:30000],
                tipo="source",
                fuente=url,
                tags=concepts[:10],
                relacionados=[r["name"] for r in related[:10]]
            )
            if obsidian_result.get("success"):
                logger.info(f"Saved to Obsidian: {obsidian_result.get('path')}")

            activity.ingest_step("Completando", 95)

            result = {
                "success": True,
                "name": title,
                "language_detected": lang,
                "was_translated": was_translated,
                "summary": summary,
                "concepts_count": len(concept_entities),
                "related_count": len(related),
                "concepts": concept_entities[:5],
                "obsidian_saved": obsidian_result.get("success", False),
                "obsidian_path": obsidian_result.get("path", ""),
            }

            activity.ingest_complete(success=True, details=f"{len(concept_entities)} conceptos")
            logger.info(f"Smart ingest completed: {title}")
            return result

        except Exception as e:
            activity.ingest_complete(success=False, details=str(e))
            logger.error(f"Smart ingest error: {e}")
            return {"error": str(e)}

    def _detect_language(self, text: str) -> str:
        """Detect language using simple heuristics."""
        if not text or len(text) < 100:
            return "unknown"

        sample = text[:1000].lower()

        spanish_indicators = ["el", "la", "los", "las", "es", "son", "de", "que", "en", "un", "una", "por", "con", "para", "como"]
        english_indicators = ["the", "a", "an", "is", "are", "of", "in", "to", "for", "with", "on", "at", "by", "from"]

        es_count = sum(1 for w in spanish_indicators if f" {w} " in f" {sample} ")
        en_count = sum(1 for w in english_indicators if f" {w} " in f" {sample} ")

        if es_count > en_count:
            return "es"
        elif en_count > 0:
            return "en"
        return "unknown"

    def _translate_text(self, text: str, target: str = "es") -> tuple:
        """Translate text using deep-translator (optional). Returns (text, translated)."""
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source="auto", target=target)
            return translator.translate(text), True
        except ImportError:
            logger.info("deep-translator not installed, skipping translation")
            return text, False
        except Exception as e:
            logger.warning(f"Translation failed: {e}, returning original")
            return text, False

    def _generate_summary(self, text: str) -> str:
        """Generate summary using LLM."""
        try:
            from core.llm_router import LLMRouter
            llm = LLMRouter()
            prompt = f"""Resume el siguiente texto en 3-5 líneas concisas, capturando los puntos principales:

{text[:5000]}

RESUMEN:"""
            result = llm.generate(prompt)
            return result[:500] if result else "Resumen no disponible"
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return "Resumen no disponible"

    def _extract_concepts(self, text: str) -> list:
        """Extract key concepts using LLM."""
        try:
            from core.llm_router import LLMRouter
            llm = LLMRouter()
            prompt = f"""Extrae 8-12 conceptos clave del siguiente texto. Devuelve solo los conceptos separados por comas:

{text[:4000]}

CONCEPTOS:"""
            result = llm.generate(prompt)
            if result:
                concepts = [c.strip() for c in result.split(",") if c.strip()]
                return concepts[:12]
            return []
        except Exception as e:
            logger.warning(f"Concept extraction failed: {e}")
            return []

    def _find_related_notes(self, concepts: list) -> list:
        """Find existing wiki notes related to concepts."""
        related = []
        for concept in concepts:
            results = self.search(concept, limit=3)
            for r in results:
                if r["name"] not in [rel["name"] for rel in related]:
                    related.append({"name": r["name"], "tipo": r.get("tipo", "unknown")})
                    if len(related) >= 10:
                        break
        return related
    
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
    
    def save_to_obsidian(self, name: str, content: str, tipo: str = "source", 
                         fuente: str = "", tags: list = None, relacionados: list = None) -> dict:
        """Save an entity as a .md file in the Obsidian wiki folder."""
        try:
            wiki_dir = Path(config.OBSIDIAN_PATH) / "wiki"
            wiki_dir.mkdir(exist_ok=True, parents=True)
            
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)[:200]
            filename = f"{safe_name}.md"
            filepath = wiki_dir / filename
            
            existing = filepath.exists()
            
            now = datetime.now().isoformat()
            tags_str = json.dumps(tags or [])
            relacionados_formatted = json.dumps(relacionados or [])
            
            frontmatter = f"""---
tipo: {tipo}
titulo: {name}
fecha_ingesta: {now}
fecha_actualizacion: {now}
fuente: {fuente}
estado: final
tags: {tags_str}
relacionados: {relacionados_formatted}
---

"""
            
            body = f"""{frontmatter}
# {name}

{content[:15000]}
"""
            
            filepath.write_text(body, encoding="utf-8")
            
            self._update_graph_add_node(safe_name, tipo, tags or [], relacionados or [])
            
            return {"success": True, "path": str(filepath), "is_new": not existing}
            
        except Exception as e:
            logger.error(f"Error saving to Obsidian: {e}")
            return {"error": str(e)}
    
    def _update_graph_add_node(self, node_id: str, tipo: str = "source", 
                              tags: list = None, relacionados: list = None):
        """Add a node to graph.json and update metadata."""
        try:
            graph_store = Path(config.OBSIDIAN_PATH) / "graph_store"
            graph_path = graph_store / "graph.json"
            meta_path = graph_store / "metadata.json"
            docs_path = graph_store / "documents.json"
            
            graph_data = {"nodes": [], "edges": [], "links_by_note": {}}
            if graph_path.exists():
                graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
            
            if node_id not in graph_data["nodes"]:
                graph_data["nodes"].append(node_id)
            
            if node_id not in graph_data["links_by_note"]:
                graph_data["links_by_note"][node_id] = []
            
            for rel in (relacionados or []):
                if isinstance(rel, dict):
                    rel_name = rel.get("name", "")
                else:
                    rel_name = str(rel)
                if rel_name and rel_name not in graph_data["nodes"]:
                    graph_data["nodes"].append(rel_name)
                edge = (node_id, rel_name) if (node_id, rel_name) not in graph_data["edges"] else None
                if edge:
                    graph_data["edges"].append(edge)
                    if rel_name not in graph_data["links_by_note"]:
                        graph_data["links_by_note"][rel_name] = []
                    if node_id not in graph_data["links_by_note"][rel_name]:
                        graph_data["links_by_note"][rel_name].append(node_id)
            
            graph_path.write_text(json.dumps(graph_data, indent=2, ensure_ascii=False), encoding="utf-8")
            
            if docs_path.exists():
                docs = json.loads(docs_path.read_text(encoding="utf-8"))
            else:
                docs = []
            if node_id not in docs:
                docs.append(node_id)
                docs_path.write_text(json.dumps(docs, indent=2), encoding="utf-8")
            
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            else:
                meta = {"total_nodos": 0, "total_aristas": 0, "hubs": [], "comunidades": {}}
            
            meta["total_nodos"] = len(graph_data["nodes"])
            meta["total_aristas"] = len(graph_data["edges"])
            meta["indexed_at"] = datetime.now().isoformat()
            
            degree = defaultdict(int)
            for src, dst in graph_data["edges"]:
                degree[src] += 1
                degree[dst] += 1
            meta["hubs"] = sorted(degree.items(), key=lambda x: -x[1])[:20]
            
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
            
            logger.info(f"Graph updated: added node {node_id}")
            
        except Exception as e:
            logger.error(f"Error updating graph: {e}")
    
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