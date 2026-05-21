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


def _slugify(name: str) -> str:
    """Generate safe id from name."""
    import re
    s = name.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[-\s]+', '_', s)
    return s[:80]


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

    def _get_quality_file(self) -> Path:
        """Get path to ingest quality history."""
        return config.DATA_DIR / "ingest_quality.json"

    def _load_quality_history(self) -> list:
        """Load quality history from JSON."""
        qf = self._get_quality_file()
        if qf.exists():
            try:
                return json.loads(qf.read_text(encoding="utf-8"))
            except:
                return []
        return []

    def _save_quality_history(self, history: list):
        """Save quality history to JSON."""
        qf = self._get_quality_file()
        qf.write_text(json.dumps(history[-500:], indent=2, ensure_ascii=False), encoding="utf-8")

    def _calculate_quality_score(self, ingest_type: str, data: dict) -> int:
        """Calculate quality score (0-100) based on ingest type and data."""
        score = 70  # Base score

        content_len = data.get("content_length", 0)

        if ingest_type == "pdf":
            pages = data.get("pages_processed", 0)
            digital = data.get("digital_pages", 0)
            ocr_pages = len(data.get("ocr_pages", []))

            if pages > 0:
                digital_ratio = digital / pages
                score += int(digital_ratio * 20)  # Up to +20 for digital content
                score += min(int(content_len / 5000), 10)  # Up to +10 for length

            if ocr_pages > 0 and data.get("has_ocr"):
                score -= 5  # Penalty for OCR

            if content_len < 1000:
                score -= 20

        elif ingest_type == "youtube":
            duration = data.get("duration_seconds", 0)
            transcript_chars = data.get("transcript_chars", 0)

            if duration > 0 and transcript_chars > 0:
                ratio = transcript_chars / duration
                score += min(int(ratio / 10), 25)  # Up to +25 for good transcript

            if transcript_chars < 500:
                score -= 25

        elif ingest_type == "url":
            html_len = data.get("html_length", 0)
            if html_len > 0 and content_len > 0:
                ratio = (content_len / html_len) * 100
                score += min(int(ratio), 15)  # Up to +15 for extraction ratio

            if content_len < 500:
                score -= 20

        concepts = data.get("concepts_found", 0)
        if concepts >= 3:
            score += min(concepts * 2, 10)
        elif concepts == 0:
            score -= 10

        return max(0, min(100, score))

    def track_ingest_quality(self, ingest_type: str, name: str, data: dict) -> dict:
        """Track quality metrics for an ingest and return quality info."""
        history = self._load_quality_history()

        quality_score = self._calculate_quality_score(ingest_type, data)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": ingest_type,
            "name": name[:100],
            "content_length": data.get("content_length", 0),
            "pages_total": data.get("pages_processed", 0),
            "pages_digital": data.get("digital_pages", 0),
            "pages_ocr": len(data.get("ocr_pages", [])),
            "concepts_found": data.get("concepts_found", 0),
            "quality_score": quality_score,
            "has_alert": quality_score < 50
        }

        history.append(entry)
        self._save_quality_history(history)

        if quality_score < 50:
            logger.warning(f"⚠️ Ingesta de baja calidad: {name} (score: {quality_score})")

        return {
            "quality_score": quality_score,
            "is_low_quality": quality_score < 50,
            "alerts": [f"Ingesta de baja calidad: {name} (score: {quality_score})"] if quality_score < 50 else []
        }

    def get_ingest_quality(self, limit: int = 20) -> dict:
        """Get quality stats for recent ingests."""
        history = self._load_quality_history()
        recent = history[-limit:] if history else []

        if not recent:
            return {
                "total": 0,
                "avg_score": 0,
                "low_quality_count": 0,
                "by_type": {},
                "recent": []
            }

        scores = [e["quality_score"] for e in recent]
        avg_score = sum(scores) / len(scores) if scores else 0
        low_quality = sum(1 for e in recent if e["quality_score"] < 50)

        by_type = {}
        for e in recent:
            t = e["type"]
            if t not in by_type:
                by_type[t] = {"count": 0, "avg_score": 0, "scores": []}
            by_type[t]["count"] += 1
            by_type[t]["scores"].append(e["quality_score"])

        for t, data in by_type.items():
            data["avg_score"] = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
            del data["scores"]

        return {
            "total": len(history),
            "avg_score": round(avg_score, 1),
            "low_quality_count": low_quality,
            "by_type": by_type,
            "recent": recent
        }

    def get_quality_alerts(self) -> list:
        """Get all quality alerts (low score ingests)."""
        history = self._load_quality_history()
        alerts = [e for e in history if e.get("has_alert") or e["quality_score"] < 50]
        return sorted(alerts, key=lambda x: x["timestamp"], reverse=True)[:10]

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
        entity_id = _slugify(name)
        
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO entities 
                (id, name, content, tipo, fuente, fecha_ingesta, fecha_actualizacion, estado, tags, relacionados)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (entity_id, name, content, tipo, fuente, now, now, estado, tags_json, relacionados_json))
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
    
    def _ensure_fts5(self):
        """Ensure FTS5 virtual table exists and is synced with entities."""
        if getattr(self, '_fts5_initialized', False):
            return
        
        try:
            self.cursor.execute("SELECT COUNT(*) FROM entities_fts")
            fts5_count = self.cursor.fetchone()[0]
        except:
            fts5_count = 0
        
        try:
            self.cursor.execute("SELECT COUNT(*) FROM entities")
            entity_count = self.cursor.fetchone()[0]
        except:
            entity_count = 0
        
        if fts5_count < entity_count or fts5_count == 0 or fts5_count > entity_count:
            try:
                self.cursor.execute("DROP TABLE IF EXISTS entities_fts")
                self.cursor.execute("CREATE VIRTUAL TABLE entities_fts USING fts5(name, content, tipo, tags)")
                
                self.cursor.execute("""
                    SELECT id, name, content, tipo, tags FROM entities
                """)
                rows = self.cursor.fetchall()
                
                for row in rows:
                    entity_id, name, content, tipo, tags = row
                    name_val = name if name else ""
                    content_val = content if content else ""
                    tipo_val = tipo if tipo else "entity"
                    tags_val = tags if tags else "[]"
                    
                    self.cursor.execute("""
                        INSERT INTO entities_fts(name, content, tipo, tags)
                        VALUES (?, ?, ?, ?)
                    """, (name_val, content_val, tipo_val, tags_val))
                
                self.conn.commit()
            except Exception as e:
                logger.debug(f"FTS5 rebuild: {e}")
        
        self._fts5_initialized = True

    STOP_WORDS = {"el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "en", "que", "es",
              "a", "al", "con", "por", "para", "se", "su", "sus", "lo", "como", "qué", "cuál", "cuáles",
              "donde", "dónde", "cuando", "cuándo", "quien", "quién", "tiene", "son", "está", "son",
              "tiene", "hacer", "sirve", "servir", "para", "sobre", "entre", "sin", "sobre", "desde",
              "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "aquel", "aquella",
              "yo", "tú", "él", "ella", "nosotros", "ellos", "ellas", "mi", "tu", "su", "me", "te",
              "nos", "os", "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
              "is", "are", "was", "were", "what", "how", "why", "when", "where", "who", "which"}

    def search(self, query: str, limit: int = 20) -> list:
        """Search wiki using FTS5 with token scoring and stop-word filtering."""
        self._ensure_fts5()
        
        raw_tokens = query.strip().lower().split()
        keywords = [t for t in raw_tokens if len(t) >= 3 and t not in self.STOP_WORDS]
        
        like_term = f"%{query}%"
        self.cursor.execute("""
            SELECT name, tipo, content, fecha_ingesta, fuente FROM entities
            WHERE name LIKE ? OR content LIKE ?
            LIMIT ?
        """, (like_term, like_term, limit))
        
        direct_results = [{"name": r[0], "tipo": r[1], "content": r[2],
                          "fecha_ingesta": r[3], "fuente": r[4]} for r in self.cursor.fetchall()]
        
        if keywords:
            name_matches = {}
            for token in keywords:
                try:
                    self.cursor.execute("""
                        SELECT name FROM entities_fts
                        WHERE entities_fts MATCH ?
                        LIMIT ?
                    """, (token, limit))
                    
                    for r in self.cursor.fetchall():
                        name = r[0]
                        name_matches[name] = name_matches.get(name, 0) + 1
                except Exception as e:
                    logger.debug(f"FTS5 token search error for '{token}': {e}")
            
            if name_matches:
                sorted_names = sorted(name_matches.items(), key=lambda x: x[1], reverse=True)
                top_names = [n for n, _ in sorted_names[:limit]]
                
                all_names_list = top_names
                placeholders = ",".join("?" * len(all_names_list))
                
                self.cursor.execute(f"""
                    SELECT name, tipo, content, fecha_ingesta, fuente FROM entities
                    WHERE name IN ({placeholders})
                """, all_names_list)
                
                name_to_result = {}
                for r in self.cursor.fetchall():
                    name_to_result[r[0]] = {
                        "name": r[0], "tipo": r[1], "content": r[2],
                        "fecha_ingesta": r[3] if len(r) > 3 else None,
                        "fuente": r[4] if len(r) > 4 else None,
                    }
                
                fts_results = [name_to_result[n] for n in all_names_list if n in name_to_result]
                
                direct_names = {r["name"] for r in direct_results}
                fts_names = {r["name"] for r in fts_results}
                shared = direct_names & fts_names
                
                results = [r for r in fts_results if r["name"] in shared]
                results += [r for r in fts_results if r["name"] not in shared]
                results += [r for r in direct_results if r["name"] not in fts_names]
                
                return results[:limit]
        
        return direct_results
    
    def get_hubs(self, limit: int = 10) -> list:
        """Get most connected entities (hubs)."""
        import json
        self.cursor.execute("SELECT name, relacionados FROM entities")
        results = []
        for row in self.cursor.fetchall():
            try:
                rels = json.loads(row[1]) if row[1] else []
                # Handle both formats: [{"name": "...", "relation": "..."}] and ["[[Name]]"]
                count = 0
                for r in rels:
                    if isinstance(r, dict):
                        if r.get("name"):
                            count += 1
                    elif isinstance(r, str) and r.strip():
                        count += 1
            except:
                count = 0
            results.append({"name": row[0], "connections": count})
        results.sort(key=lambda x: x["connections"], reverse=True)
        return results[:limit]
    
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

    def deduplicate(self) -> dict:
        """Remove duplicate entities keeping the most complete (longest content)."""
        cur = self.cursor
        
        cur.execute("""
            SELECT name, COUNT(*) as cnt, GROUP_CONCAT(rowid) as rowids
            FROM entities 
            GROUP BY name 
            HAVING cnt > 1
        """)
        dupes = cur.fetchall()
        
        total_deleted = 0
        for name, cnt, rowids_str in dupes:
            rowids = [int(x) for x in rowids_str.split(",")]
            
            cur.execute("""
                SELECT rowid, length(content) as clen FROM entities 
                WHERE rowid IN ({}) ORDER BY clen DESC
            """.format(",".join("?" * len(rowids))), rowids)
            
            rows = cur.fetchall()
            keep_rowid = rows[0][0]
            delete_rowids = [r[0] for r in rows[1:]]
            
            for rid in delete_rowids:
                cur.execute("DELETE FROM entities WHERE rowid = ?", (rid,))
                total_deleted += 1
        
        self.conn.commit()
        logger.info(f"Deduplication: deleted {total_deleted} duplicates, kept {len(dupes)}")
        return {"deleted": total_deleted, "kept": len(dupes)}
    
    def fix_null_ids(self) -> dict:
        """Generate id from name for entities with NULL id."""
        cur = self.cursor
        
        cur.execute("SELECT rowid, name FROM entities WHERE id IS NULL")
        nulls = cur.fetchall()
        
        fixed = 0
        skipped = 0
        for rowid, name in nulls:
            base_id = _slugify(name)
            entity_id = base_id
            
            counter = 1
            while True:
                cur.execute("SELECT rowid FROM entities WHERE id = ? AND rowid != ?", (entity_id, rowid))
                if not cur.fetchone():
                    break
                entity_id = f"{base_id}_{counter}"
                counter += 1
                if counter > 100:
                    break
            
            cur.execute("UPDATE entities SET id = ? WHERE rowid = ?", (entity_id, rowid))
            fixed += 1
        
        self.conn.commit()
        logger.info(f"Fixed {fixed} NULL ids, skipped {skipped}")
        return {"fixed": fixed, "skipped": skipped}
    
    def backfill_tags(self) -> dict:
        """Auto-tag entities with tags='[]' based on content keywords."""
        cur = self.cursor
        
        cur.execute("SELECT rowid, name, tipo, content FROM entities WHERE tags = '[]'")
        untagged = cur.fetchall()
        
        KEYWORD_MAP = {
            "transformer": ["transformers", "attention", "self-attention", "encoder", "decoder", "seq2seq"],
            "lstm": ["lstm", "long short-term", "memory", "recurrent", "rnn", "gru"],
            "optimization": ["optimizer", "adam", "sgd", "gradient", "loss", "training", "backpropagation"],
            "reinforcement": ["reinforcement", "reward", "policy", "agent", "environment", "rl"],
            "nlp": ["nlp", "language model", "token", "embedding", "text", "corpus", "vocabulary"],
            "vision": ["image", "cnn", "convolutional", "vision", "object detection", "segmentation"],
            "graph": ["graph", "node", "edge", "knowledge graph", "relation"],
            "rag": ["rag", "retrieval", "retrieval-augmented", "vector database", "faiss"],
            "llm": ["llm", "large language model", "gpt", "bert", "chatgpt", "claude", "openai"],
            "fine-tuning": ["fine-tuning", "lora", "qlora", "adapter", "peft", "fine-tune"],
            "agent": ["agent", "tool", "reasoning", "planning", "autonomous"],
            "memory": ["memory", "forget", "retention", "episodic", "semantic"],
            "neural_network": ["neural network", "layer", "weight", "bias", "activation"],
            "research": ["paper", "arxiv", "conference", "research", "study", "experiment"],
            "hardware": ["gpu", "cpu", "tpu", "hardware", "memory", "compute", "flop"],
            "quantization": ["quantization", "quantize", "int8", "int4", "pruning", "compression"],
            "evaluation": ["benchmark", "perplexity", "accuracy", "bleu", "metric", "evaluation"],
            "training": ["training", "entrenamiento", "pre-training", "finetuning", "epoch"],
        }
        
        tipo_map = {
            "video": ["video", "youtube", "charla", "talk", "presentacion"],
            "pdf": ["pdf", "paper", "articulo", "arxiv"],
            "concept": ["concepto", "idea", "teoria", "theory"],
            "source": ["source", "fuente"],
            "entity": ["entity", "persona", "organizacion", "empresa"],
        }
        
        fixed = 0
        for rowid, name, tipo, content in untagged:
            content_lower = (content or "").lower()
            name_lower = name.lower()
            tags = set()
            
            tags.add("legacy")
            
            if tipo:
                tags.add(tipo.lower())
                if tipo.lower() in tipo_map:
                    tags.add(f"tipo-{tipo.lower()}")
            
            for tag, keywords in KEYWORD_MAP.items():
                if any(kw in content_lower or kw in name_lower for kw in keywords):
                    tags.add(tag)
            
            for tag, keywords in tipo_map.items():
                for kw in keywords:
                    if kw in content_lower or kw in tipo.lower():
                        tags.add(tag)
                        break
            
            if "lora" in name_lower or "lora" in content_lower:
                tags.add("lora")
            if "gpt" in name_lower or "gpt" in content_lower:
                tags.add("llm")
            if "research" in name_lower:
                tags.add("research")
            
            tags_list = list(tags) if tags else ["legacy", "untagged"]
            tags_json = json.dumps(tags_list)
            
            cur.execute("UPDATE entities SET tags = ? WHERE rowid = ?", (tags_json, rowid))
            fixed += 1
        
        self.conn.commit()
        logger.info(f"Backfilled tags for {fixed} entities")
        return {"fixed": fixed}

    def save_research_proposal(self, pregunta: str, propuesta: str, modo: str, refs: list) -> dict:
        """Save research proposal as a wiki note with frontmatter."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(pregunta)[:50]
        name = f"research_proposal_{timestamp}"

        content_lines = []
        content_lines.append(f"# Propuesta de Investigación")
        content_lines.append(f"**Pregunta Original:** {pregunta}")
        content_lines.append(f"**Modo:** {modo}")
        content_lines.append(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content_lines.append("")
        content_lines.append("---")
        content_lines.append("")
        content_lines.append("## Propuesta")
        content_lines.append(propuesta)
        content_lines.append("")
        content_lines.append("## Referencias")
        for ref in refs:
            ref_name = ref.get("name", "Sin nombre")
            ref_tipo = ref.get("tipo", "entity")
            ref_preview = ref.get("content_preview", "")[:200]
            content_lines.append(f"### {ref_name}")
            content_lines.append(f"**Tipo:** {ref_tipo}")
            content_lines.append(f"**Extracto:** {ref_preview}")
            content_lines.append("")

        content = "\n".join(content_lines)

        result = self.add_entity(
            name=name,
            content=content,
            tipo="synthesis",
            fuente="research_agent",
            estado="draft",
            tags=["research", "proposal", modo, "investigacion"],
            relacionados=[]
        )

        logger.info(f"Research proposal saved: {name}")
        return result

    def get_last_source(self, content_type: str = "all") -> dict:
        """Get the last ingested source (PDF, YouTube, URL).

        Args:
            content_type: "all", "pdf", "youtube", "url"
        """
        # Build specific query based on content_type
        if content_type == "pdf":
            # Get last PDF - from temp folder or .pdf extension
            self.cursor.execute("""
                SELECT name, tipo, content, fuente, fecha_ingesta
                FROM entities
                WHERE tipo = 'source'
                AND fuente LIKE '%temp%'
                ORDER BY fecha_ingesta DESC
                LIMIT 1
            """)
        elif content_type == "youtube":
            self.cursor.execute("""
                SELECT name, tipo, content, fuente, fecha_ingesta
                FROM entities
                WHERE tipo = 'video'
                ORDER BY fecha_ingesta DESC
                LIMIT 1
            """)
        elif content_type == "url":
            self.cursor.execute("""
                SELECT name, tipo, content, fuente, fecha_ingesta
                FROM entities
                WHERE tipo = 'source'
                AND fuente LIKE 'http%'
                AND fuente NOT LIKE '%youtube%'
                AND fuente NOT LIKE '%temp%'
                ORDER BY fecha_ingesta DESC
                LIMIT 1
            """)
        else:  # all - get last source or video
            self.cursor.execute("""
                SELECT name, tipo, content, fuente, fecha_ingesta
                FROM entities
                WHERE tipo IN ('source', 'video')
                AND fuente IS NOT NULL
                AND fuente != ''
                AND fuente NOT LIKE '%obsidian%'
                ORDER BY fecha_ingesta DESC
                LIMIT 1
            """)

        row = self.cursor.fetchone()
        if row:
            return {
                "name": row[0],
                "tipo": row[1],
                "content": row[2],
                "fuente": row[3],
                "fecha": row[4]
            }
        return None

    def get_last_ingested(self, limit: int = 5) -> list:
        """Get the last N ingested sources (PDFs, YouTubes, URLs) ordered by fecha_ingesta."""
        # Get only actual content sources (video, source with actual files/URLs)
        self.cursor.execute("""
            SELECT name, tipo, content, fuente, fecha_ingesta
            FROM entities
            WHERE (
                (tipo = 'video')
                OR (tipo = 'source' AND fuente IS NOT NULL AND fuente != '' 
                    AND fuente NOT LIKE '%obsidian%' 
                    AND (fuente LIKE '%temp%' OR fuente LIKE '%.pdf%' OR fuente LIKE 'http%'))
            )
            ORDER BY fecha_ingesta DESC
            LIMIT ?
        """, (limit,))
        results = []
        for row in self.cursor.fetchall():
            results.append({
                "name": row[0],
                "tipo": row[1],
                "content": row[2],
                "fuente": row[3],
                "fecha": row[4]
            })
        return results

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

    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video."""
        return "youtube.com" in url or "youtu.be" in url

    def _check_node_js(self) -> tuple:
        """Check if Node.js is available. Returns (available, path)."""
        import shutil
        import subprocess
        import os
        
        node_path = shutil.which('node')
        if node_path:
            try:
                result = subprocess.run(['node', '--version'], 
                                       capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return True, node_path
            except:
                pass
        
        if os.name == 'nt':
            program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
            node_paths = [
                os.path.join(program_files, 'nodejs', 'node.exe'),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'nodejs', 'node.exe'),
                r"C:\Program Files\nodejs\node.exe",
            ]
            for path in node_paths:
                if os.path.exists(path):
                    os.environ['PATH'] = os.path.dirname(path) + ';' + os.environ.get('PATH', '')
                    return True, path
        
        return False, None

    def _extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from various URL formats."""
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        if "youtube.com" in parsed.hostname or "www.youtube.com" in parsed.hostname:
            qs = urllib.parse.parse_qs(parsed.query)
            return qs.get("v", [None])[0]
        elif "youtu.be" in parsed.hostname:
            return parsed.path.lstrip("/").split("?")[0]
        return None

    def _extract_youtube_transcript(self, video_url: str) -> tuple:
        """Extract transcript from YouTube video. Returns (transcript, metadata).

        Strategy (in order):
        1. youtube-transcript-api (fast, no JS runtime needed)
        2. yt-dlp with remote EJS solver + Node.js (if installed)
        """
        transcript = ""
        metadata = {}

        # ─── Method 1: youtube-transcript-api (preferred) ────────────────
        video_id = self._extract_video_id(video_url)
        if video_id:
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                logger.info(f"Trying youtube-transcript-api for {video_id}...")

                ytt = YouTubeTranscriptApi()
                fetched = ytt.fetch(video_id, languages=["es", "en"])
                snippets = list(fetched)

                if snippets:
                    lines = []
                    for s in snippets:
                        # Handle both object attributes (v1.0+) and dicts (older versions)
                        start = s.get("start", 0) if isinstance(s, dict) else getattr(s, "start", 0)
                        text = s.get("text", "").strip() if isinstance(s, dict) else getattr(s, "text", "").strip()
                        if text:
                            minutes = int(start // 60)
                            seconds = int(start % 60)
                            lines.append(f"[{minutes:02d}:{seconds:02d}] {text}")
                    transcript = "\n".join(lines)
                    logger.info(f"youtube-transcript-api OK: {len(transcript)} chars, {len(snippets)} segments")
            except Exception as e:
                logger.warning(f"youtube-transcript-api failed: {e}")

        # ─── Method 2: yt-dlp (fallback) ────────────────────────────────
        if not transcript:
            try:
                import yt_dlp
                logger.info("Falling back to yt-dlp for transcript...")

                node_available, node_path = self._check_node_js()

                ydl_opts = {
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['es', 'en', 'en-US', 'en-GB'],
                    'skip_download': True,
                    'quiet': True,
                }

                # Enable JS runtime if Node.js is available
                if node_available:
                    ydl_opts['js_runtimes'] = {'node': {}}
                    logger.info(f"Node.js found at: {node_path}")
                else:
                    logger.warning(
                        "Node.js not found. yt-dlp may fail to solve YouTube JS challenges. "
                        "Install Node.js: https://nodejs.org/"
                    )

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)

                # Save metadata from yt-dlp info
                metadata = {
                    'title': info.get('title', ''),
                    'description': info.get('description', '')[:2000],
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'thumbnail': info.get('thumbnail', ''),
                }

                logger.info(f"yt-dlp info: subtitles={list(info.get('subtitles', {}).keys())}, "
                            f"auto-captions={list(info.get('automatic_captions', {}).keys())[:5]}")

                # Try to find subtitle source
                subtitle_langs = ['es', 'es-ES', 'es-419', 'en', 'en-US', 'en-GB']
                subs_dict = info.get('subtitles', {})
                auto_dict = info.get('automatic_captions', {})
                chosen_subs = None

                # Prefer manual subtitles
                for lang in subtitle_langs:
                    if subs_dict.get(lang):
                        chosen_subs = subs_dict[lang]
                        logger.info(f"Using manual subtitles: {lang}")
                        break

                # Then auto-captions
                if not chosen_subs:
                    for lang in subtitle_langs:
                        if auto_dict.get(lang):
                            chosen_subs = auto_dict[lang]
                            logger.info(f"Using auto-captions: {lang}")
                            break

                # Then first available
                if not chosen_subs and auto_dict:
                    first_lang = next(iter(auto_dict.keys()))
                    chosen_subs = auto_dict[first_lang]
                    logger.info(f"Using first available auto-caption: {first_lang}")

                # Download the subtitle URL
                if chosen_subs:
                    import time
                    import requests as req

                    for fmt_entry in chosen_subs[:3]:
                        sub_url = fmt_entry.get('url', '')
                        if not sub_url:
                            continue

                        for attempt in range(3):
                            try:
                                if attempt > 0:
                                    time.sleep(3 ** attempt)
                                resp = req.get(sub_url, timeout=20,
                                               headers={'User-Agent': 'Mozilla/5.0'})
                                if resp.ok:
                                    if 'vtt' in resp.headers.get('Content-Type', '').lower() or sub_url.endswith('.vtt'):
                                        texts = self._parse_vtt_content(resp.text)
                                    else:
                                        texts = self._parse_srt_content(resp.text)
                                    if texts:
                                        transcript = "\n".join(texts)
                                        logger.info(f"yt-dlp transcript OK: {len(transcript)} chars")
                                        break
                                elif resp.status_code == 429:
                                    logger.warning("Rate limited (429), waiting 10s...")
                                    time.sleep(10)
                            except Exception as e:
                                logger.warning(f"Subtitle download error: {e}")

                        if transcript:
                            break
                else:
                    logger.warning("yt-dlp: no subtitles available for this video")

            except ImportError:
                logger.warning("yt-dlp not installed (pip install yt-dlp)")
            except Exception as e:
                logger.warning(f"yt-dlp transcript extraction failed: {e}")

        # ─── Metadata fallback (if not obtained from yt-dlp) ────────────
        if not metadata:
            metadata = self._extract_youtube_metadata(video_url)

        return transcript, metadata

    def _extract_youtube_metadata(self, url: str) -> dict:
        """Extract enhanced metadata from YouTube URL."""
        try:
            import yt_dlp
            ydl_opts = {'quiet': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', ''),
                'description': info.get('description', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'uploader': info.get('uploader', ''),
                'upload_date': info.get('upload_date', ''),
                'tags': info.get('tags', [])[:20],
                'category': info.get('categories', [''])[0],
                'thumbnail': info.get('thumbnail', ''),
            }
        except Exception as e:
            logger.warning(f"YouTube metadata extraction failed: {e}")
            return {}
    
    def _parse_vtt_content(self, content: str) -> list:
        """Parse WebVTT subtitle format."""
        texts = []
        current_start = 0
        current_text = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            if '-->' in line:
                try:
                    start_str = line.split('-->')[0].strip()
                    parts = start_str.split(':')
                    if len(parts) >= 2:
                        minutes = int(parts[-2])
                        seconds_parts = parts[-1].split('.')
                        seconds = int(seconds_parts[0])
                        milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
                        current_start = minutes * 60 + seconds + milliseconds / 1000
                except:
                    pass
                continue
            
            if line and not line.startswith('WEBVTT') and not line.startswith('NOTE'):
                if line.startswith('<'):
                    continue
                clean_text = re.sub(r'<[^>]+>', '', line)
                if clean_text.strip():
                    current_text.append(clean_text.strip())
            elif current_text:
                texts.append(f"[{int(current_start // 60):02d}:{int(current_start % 60):02d}] {' '.join(current_text)}")
                current_text = []
        
        if current_text:
            texts.append(f"[{int(current_start // 60):02d}:{int(current_start % 60):02d}] {' '.join(current_text)}")
        
        return texts
    
    def _parse_srt_content(self, content: str) -> list:
        """Parse SRT subtitle format."""
        from bs4 import BeautifulSoup
        
        texts = []
        
        soup = BeautifulSoup(content, 'html.parser')
        
        for seg in soup.find_all('text'):
            text = seg.get_text(strip=True)
            if text:
                try:
                    start = float(seg.get('start', 0))
                    texts.append(f"[{int(start // 60):02d}:{int(start % 60):02d}] {text}")
                except:
                    texts.append(text)
        
        if not texts:
            for line in content.split('\n'):
                line = line.strip()
                if '-->' in line:
                    try:
                        start_str = line.split('-->')[0].strip().replace(',', '.')
                        parts = start_str.split(':')
                        if len(parts) >= 2:
                            minutes = int(parts[-2])
                            seconds_parts = parts[-1].split('.')
                            seconds = int(seconds_parts[0])
                            milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
                            start = minutes * 60 + seconds + milliseconds / 1000
                        elif len(parts) == 1:
                            seconds = int(parts[0])
                            start = seconds
                        else:
                            start = 0
                    except:
                        start = 0
                elif line and line.isdigit():
                    continue
                elif line:
                    texts.append(line)
        
        return texts

    def _ingest_youtube(self, url: str, translate_to: str, activity) -> dict:
        """Special ingestion for YouTube videos."""
        try:
            activity.ingest_step("Extrayendo metadata", 10)
            metadata = self._extract_youtube_metadata(url)
            
            activity.ingest_step("Extrayendo transcript", 30)
            transcript, _ = self._extract_youtube_transcript(url)
            
            title = metadata.get('title', url)
            description = metadata.get('description', '')
            uploader = metadata.get('uploader', '')
            duration = metadata.get('duration', 0)
            views = metadata.get('view_count', 0)
            upload_date = metadata.get('upload_date', '')
            tags = metadata.get('tags', [])
            
            activity.ingest_step("Procesando contenido", 50)
            
            if transcript:
                content_to_process = f"TRANSCRIPCIÓN DEL VIDEO:\n{transcript}"
            else:
                content_to_process = f"DESCRIPCIÓN:\n{description}" if description else ""
            
            if not content_to_process:
                return {"error": "No se pudo extraer contenido del video"}
            
            activity.ingest_step("Detectando idioma", 60)
            lang = self._detect_language(content_to_process)
            logger.info(f"Detected language: {lang}, target: {translate_to}")
            
            translated_content = content_to_process
            was_translated = False
            if lang != translate_to and lang != "unknown":
                activity.ingest_step("Traduciendo", 70)
                translated_content, was_translated = self._translate_text(content_to_process, target=translate_to)
            
            activity.ingest_step("Generando resumen", 75)
            summary = self._generate_summary(translated_content[:8000])
            
            activity.ingest_step("Extrayendo conceptos", 80)
            logger.info(f"Extracting concepts from {len(translated_content)} chars of content...")
            concepts = self._extract_concepts(translated_content[:8000])
            logger.info(f"Extracted concepts: {concepts}")
            if tags:
                concepts.extend([t for t in tags[:5] if t not in concepts])
            
            activity.ingest_step("Guardando en wiki", 90)
            
            dur_min = duration // 60 if duration else 0
            dur_sec = duration % 60 if duration else 0
            
            content_full = f"""# {title}

**Duración:** {dur_min}:{str(dur_sec).zfill(2)} | **Visitas:** {views:,}
**Autor:** {uploader} | **Fecha:** {upload_date or 'N/A'}

## Transcripción
{translated_content[:25000]}

## Metadatos
- **Tags:** {', '.join(tags[:15]) if tags else 'N/A'}
- **Descripción:** {description[:1000] if description else 'N/A'}
"""
            
            entity_tags = concepts[:10] + ["youtube", "video"]
            
            self.add_entity(
                name=title,
                content=content_full,
                tipo="video",
                fuente=url,
                estado="final",
                tags=entity_tags,
                relacionados=[]
            )
            
            self.save_to_obsidian(
                name=title,
                content=content_full,
                tipo="video",
                fuente=url,
                tags=entity_tags,
                relacionados=[]
            )
            
            for concept in concepts[:6]:
                clean = concept.strip()[:100]
                if clean and len(clean) > 2:
                    self.add_entity(
                        name=clean,
                        content=f"Concepto del video: {title}",
                        tipo="concept",
                        fuente=url,
                        estado="final",
                        tags=["auto-generated", "youtube"]
                    )
            
            result = {
                "success": True,
                "name": title,
                "language_detected": lang,
                "was_translated": was_translated,
                "has_transcript": bool(transcript),
                "summary": summary,
                "concepts_count": len(concepts[:6]),
                "concepts": concepts[:5],
                "metadata": {
                    "duration": duration,
                    "views": views,
                    "uploader": uploader,
                    "upload_date": upload_date,
                },
                "obsidian_saved": True,
            }

            quality_info = self.track_ingest_quality("youtube", title, {
                "content_length": len(translated_content),
                "duration_seconds": duration,
                "transcript_chars": len(transcript) if transcript else 0,
                "concepts_found": len(concepts)
            })
            result["quality_score"] = quality_info["quality_score"]
            result["quality_alerts"] = quality_info.get("alerts", [])

            activity.ingest_complete(success=True, details=f"{len(concepts)} conceptos, transcript={bool(transcript)}, quality={quality_info['quality_score']}")
            logger.info(f"YouTube ingest completed: {title}, transcript={bool(transcript)}, quality={quality_info['quality_score']}")
            return result
            
        except Exception as e:
            activity.ingest_complete(success=False, details=str(e))
            logger.error(f"YouTube ingest error: {e}")
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
        - YouTube: metadata + transcript extraction + translation
        """
        import requests
        from bs4 import BeautifulSoup
        from core.live_activity import get_tracker

        activity = get_tracker()
        activity.ingest_start(url)
        logger.info(f"Smart ingest starting for: {url}")

        is_youtube = self._is_youtube_url(url)
        
        if is_youtube:
            return self._ingest_youtube(url, translate_to, activity)

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
                "content_length": len(translated_content),
                "html_length": len(resp.text),
            }

            quality_info = self.track_ingest_quality("url", title, {
                "content_length": len(translated_content),
                "html_length": len(resp.text),
                "concepts_found": len(concept_entities)
            })
            result["quality_score"] = quality_info["quality_score"]
            result["quality_alerts"] = quality_info.get("alerts", [])

            activity.ingest_complete(success=True, details=f"{len(concept_entities)} conceptos, quality={quality_info['quality_score']}")
            logger.info(f"Smart ingest completed: {title}, quality={quality_info['quality_score']}")
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

        spanish_indicators = ["el", "la", "los", "las", "es", "son", "de", "que", "en", "un", "una", "por", "con", "para", "como", "está", "pero", "porque", "este", "esta", "tiene", "hace", "solo", "más", "bien", "ahora", "cuando", "así"]
        english_indicators = ["the", "a", "an", "is", "are", "of", "in", "to", "for", "with", "on", "at", "by", "from", "this", "that", "have", "has", "will", "would", "could", "should", "just", "like", "get", "one"]

        es_count = sum(1 for w in spanish_indicators if f" {w} " in f" {sample} ")
        en_count = sum(1 for w in english_indicators if f" {w} " in f" {sample} ")

        # Require at least 2 matches to be confident
        if es_count >= 2 and es_count >= en_count:
            return "es"
        elif en_count >= 2 and en_count >= es_count:
            return "en"
        elif es_count > en_count:
            return "es"
        elif en_count > 0:
            return "en"
        return "unknown"

    def _translate_text(self, text: str, target: str = "es") -> tuple:
        """Translate text using deep-translator (with chunking for long texts). Returns (text, translated)."""
        try:
            from deep_translator import GoogleTranslator
            
            max_chunk = 4500
            if len(text) <= max_chunk:
                translator = GoogleTranslator(source="auto", target=target)
                return translator.translate(text), True
            
            # Chunk the text
            chunks = []
            lines = text.split('\n')
            current_chunk = ""
            
            for line in lines:
                if len(current_chunk) + len(line) + 1 > max_chunk:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += "\n" + line if current_chunk else line
            
            if current_chunk:
                chunks.append(current_chunk)
            
            logger.info(f"Translating {len(chunks)} chunks...")
            translated_chunks = []
            for i, chunk in enumerate(chunks):
                translator = GoogleTranslator(source="auto", target=target)
                translated_chunks.append(translator.translate(chunk))
                if i < len(chunks) - 1:
                    import time
                    time.sleep(0.5)  # Rate limiting
            
            return "\n".join(translated_chunks), True
            
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
            prompt = f"""Extrae 10-15 conceptos clave del siguiente texto. 
Los conceptos deben ser los más importantes y relevantes del texto.
Devuelve SOLO los conceptos separados por comas (sin números, sin explicaciones):

{text[:6000]}

CONCEPTOS:"""
            result = llm.generate(prompt)
            if result:
                concepts = [c.strip() for c in result.split(",") if c.strip()]
                logger.info(f"LLM returned {len(concepts)} concepts: {concepts}")
                return concepts[:15]
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
    
    def _check_ocr_model_available(self) -> bool:
        """Verify that the configured OCR model is loaded in Ollama."""
        import requests as _req
        try:
            resp = _req.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
            if not resp.ok:
                return False
            models = [m["name"] for m in resp.json().get("models", [])]
            # Accept exact match OR prefix match (e.g. "glm-ocr" matches "glm-ocr:latest")
            ocr_model = config.OCR_MODEL
            return any(
                m == ocr_model or m.startswith(ocr_model.split(":")[0])
                for m in models
            )
        except Exception as e:
            logger.warning(f"Could not contact Ollama to check OCR model: {e}")
            return False

    def extract_with_ocr(self, file_path: str, max_retries: int = 2) -> str:
        """Extract text from image using Ollama vision model (config.OCR_MODEL)."""
        import time
        from ollama import Client

        ocr_model = config.OCR_MODEL

        # Verify the model is available before trying
        if not self._check_ocr_model_available():
            logger.error(
                f"OCR model '{ocr_model}' is not available in Ollama. "
                f"Run: ollama pull {ocr_model}"
            )
            return ""

        client = Client(config.OLLAMA_BASE_URL)

        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
        except Exception as e:
            logger.error(f"Cannot read image file: {e}")
            return ""

        prompts = [
            "Eres un OCR especializado. Extrae TODO el texto de esta imagen. Mantén la estructura y párrafos. Devuelve solo el texto EXTRAÍDO, sin comentarios.",
            "Extract ALL text visible in this image. Preserve structure and formatting. Output only the extracted text.",
        ]

        for prompt_idx, prompt_text in enumerate(prompts):
            for attempt in range(max_retries):
                try:
                    logger.info(f"OCR attempt {attempt + 1} with prompt {prompt_idx + 1} using '{ocr_model}'...")
                    resp = client.chat(
                        model=ocr_model,
                        messages=[{
                            "role": "user",
                            "content": prompt_text,
                            "images": [img_bytes],
                        }],
                        options={"num_ctx": 8192},
                    )
                    text = resp.message.content.strip()
                    if text and len(text) > 10:
                        logger.info(f"OCR success: {len(text)} chars from {Path(file_path).name}")
                        return text
                    else:
                        logger.warning(f"OCR returned empty or too short: {len(text)} chars")
                except Exception as ocr_error:
                    logger.warning(f"OCR attempt {attempt + 1} failed: {ocr_error}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
            logger.warning(f"Prompt {prompt_idx + 1} failed, trying next...")

        logger.error(f"OCR failed after {max_retries} attempts for {file_path}")
        return ""

    def _process_pdf_page_ocr(self, pdf_path: str, page_num: int, dpi: int = 200, timeout: int = 180) -> str:
        """OCR a single PDF page using PyMuPDF + Ollama (config.OCR_MODEL).

        Steps:
        1. Render the PDF page to PNG with PyMuPDF (no poppler needed)
        2. Send PNG bytes to Ollama vision model via images field
        """
        ocr_model = config.OCR_MODEL

        # Verify the model is available before trying
        if not self._check_ocr_model_available():
            logger.error(
                f"OCR model '{ocr_model}' is not available in Ollama. "
                f"Run: ollama pull {ocr_model}"
            )
            return ""

        try:
            import fitz
            from ollama import Client

            logger.info(f"Converting page {page_num + 1} to image with PyMuPDF...")

            # Render PDF page to PNG
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num)
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            config.TEMP_DIR.mkdir(exist_ok=True, parents=True)
            temp_img = config.TEMP_DIR / f"ocr_page_{page_num}.png"
            pix.save(str(temp_img))
            doc.close()

            logger.info(f"Page {page_num + 1} rendered ({temp_img.stat().st_size} bytes), sending to '{ocr_model}'...")

            with open(temp_img, "rb") as f:
                img_bytes = f.read()

            client = Client(config.OLLAMA_BASE_URL)
            resp = client.chat(
                model=ocr_model,
                messages=[{
                    "role": "user",
                    "content": "Extract ALL text from this image. Preserve structure and formatting. Output only the extracted text.",
                    "images": [img_bytes],
                }],
                options={"num_ctx": 8192},
            )

            text = resp.message.content.strip()

            try:
                temp_img.unlink()
            except Exception:
                pass

            if text:
                logger.info(f"Page {page_num + 1}: OCR extracted {len(text)} chars")
            else:
                logger.warning(f"Page {page_num + 1}: OCR returned empty")
            return text

        except ImportError as e:
            logger.error(f"Missing dependency for OCR: {e}")
            return ""
        except Exception as e:
            logger.error(f"OCR failed on page {page_num + 1}: {e}")
            return ""

    def ingest_file(self, file_path: str) -> dict:
        """Ingest a local file based on its extension."""
        path = Path(file_path)
        
        if not path.exists():
            return {"error": f"File not found: {file_path}"}
        
        ext = path.suffix.lower()
        
        if ext == ".pdf":
            return self.ingest_pdf(str(path))
        elif ext in [".txt", ".md", ".csv"]:
            return self._ingest_text_file(str(path))
        elif ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]:
            return self.ingest_image(str(path))
        elif ext == ".docx":
            return self._ingest_docx(str(path))
        else:
            return {"error": f"Unsupported file type: {ext}"}

    def _ingest_text_file(self, file_path: str) -> dict:
        """Ingest plain text file."""
        try:
            content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            name = Path(file_path).stem
            return self.add_entity(
                name=name,
                content=content[:50000],
                tipo="source",
                fuente=file_path,
                estado="final",
                tags=["text-file"]
            )
        except Exception as e:
            return {"error": str(e)}

    def ingest_image(self, file_path: str) -> dict:
        """Ingest an image file using OCR."""
        try:
            text = self.extract_with_ocr(file_path)
            
            if not text:
                return {"error": "OCR no pudo extraer texto de la imagen"}
            
            name = Path(file_path).stem
            return self.add_entity(
                name=name,
                content=text,
                tipo="image-ocr",
                fuente=file_path,
                estado="final",
                tags=["ocr", "image"]
            )
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_pdf_pages(self, pdf_path: str) -> dict:
        """Analizar páginas del PDF para detectar cuáles necesitan OCR.
        
        Detecta páginas escaneadas basándose en:
        - Cantidad de texto (bajo = probable escaneo)
        - Densidad de caracteres (baja = probable escaneo)  
        - Caracteres no imprimibles (alto = probable imagen)
        
        Returns:
            dict con 'pages_need_ocr' (lista de índices), 'pages_with_text' (lista)
        """
        import PyPDF2
        import re
        
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            
            pages_need_ocr = []
            pages_with_text = []
            
            for i in range(num_pages):
                page_text = reader.pages[i].extract_text() or ""
                text_stripped = page_text.strip()
                text_len = len(text_stripped)
                
                # Calcular densidad: proporción de caracteresalfabéticos vs total
                if text_len > 0:
                    alpha_chars = len(re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ]', text_stripped))
                    density = alpha_chars / text_len
                else:
                    density = 0
                
                # Página necesita OCR solo si:
                # - Menos de 200 caracteres (probable escaneo)
                # - O completamente vacía
                needs_ocr = (
                    text_len < 200 or 
                    text_len == 0
                )
                
                if needs_ocr:
                    pages_need_ocr.append(i)
                else:
                    pages_with_text.append(i)
            
            logger.info(f"PDF analysis: {len(pages_with_text)} páginas con texto, {len(pages_need_ocr)} necesitan OCR")
            return {
                "total_pages": num_pages,
                "pages_need_ocr": pages_need_ocr,
                "pages_with_text": pages_with_text
            }

    def ingest_pdf(self, file_path: str, use_ocr_fallback: bool = True, force_ocr: bool = False) -> dict:
        """Ingest PDF file with intelligent page-by-page OCR.
        
        1. Analiza cada página para detectar cuáles necesitan OCR
        2. Extrae texto digital de páginas con texto
        3. Aplica OCR solo a páginas escaneadas
        4. Combina todos los resultados
        """
        try:
            # pypdf is the maintained successor of PyPDF2 (same API)
            try:
                from pypdf import PdfReader
            except ImportError:
                import PyPDF2 as _pypdf2
                PdfReader = _pypdf2.PdfReader

            import fitz  # PyMuPDF — needed here for metadata extraction

            logger.info(f"Starting PDF ingestion: {Path(file_path).name}")

            # 1. Analyze pages to detect which need OCR
            page_analysis = self._analyze_pdf_pages(file_path)
            pages_need_ocr = page_analysis["pages_need_ocr"]
            pages_with_text = page_analysis["pages_with_text"]
            num_pages = page_analysis["total_pages"]

            logger.info(f"Page analysis: {len(pages_with_text)} digital, {len(pages_need_ocr)} need OCR")

            # 2. Extract digital text from pages that have text
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                logger.info(f"PDF has {num_pages} pages, extracting digital text...")

                page_texts = {}
                
                # Extract digital text from pages that have it
                for page_idx in pages_with_text:
                    page_text = reader.pages[page_idx].extract_text() or ""
                    page_texts[page_idx] = page_text

                digital_chars = sum(len(t.strip()) for t in page_texts.values())
                logger.info(f"Extracted {digital_chars} chars from {len(pages_with_text)} digital pages")

            # 3. Apply OCR to pages that need it
            ocr_pages = []
            ocr_texts = {}
            
            should_use_ocr = force_ocr or (use_ocr_fallback and len(pages_need_ocr) > 0)
            
            if should_use_ocr and self._check_ocr_model_available():
                logger.info(f"Applying OCR to {len(pages_need_ocr)} pages...")
                for page_idx in pages_need_ocr:
                    logger.info(f"OCR processing page {page_idx + 1}/{num_pages}...")
                    ocr_text = self._process_pdf_page_ocr(file_path, page_idx)
                    if ocr_text and len(ocr_text.strip()) > 50:
                        ocr_texts[page_idx] = ocr_text
                        ocr_pages.append(page_idx + 1)  # 1-indexed for display
                        logger.info(f"Page {page_idx + 1}: OCR extracted {len(ocr_text)} chars")
                    else:
                        logger.warning(f"Page {page_idx + 1}: OCR failed or empty, using digital if available")
                        # Fallback: keep digital text even if minimal
                        if page_idx in page_texts and page_texts[page_idx].strip():
                            ocr_texts[page_idx] = page_texts[page_idx]
            else:
                logger.info("Skipping OCR (not needed or model unavailable)")

            # 4. Combine all page texts in order
            combined_parts = []
            for i in range(num_pages):
                if i in ocr_texts:
                    combined_parts.append(ocr_texts[i])
                elif i in page_texts:
                    combined_parts.append(page_texts[i])
            
            full_text = "\n".join(combined_parts)
            
            if not full_text.strip():
                return {"error": "No se pudo extraer texto del PDF"}

            # Get title from PDF metadata
            name = Path(file_path).stem
            try:
                doc = fitz.open(file_path)
                pdf_title = doc.metadata.get("title", "")
                if pdf_title and len(pdf_title.strip()) > 5:
                    name = pdf_title.strip()[:200]
                    logger.info(f"Using PDF title: {name}")
                doc.close()
            except Exception as e:
                logger.warning(f"Could not extract PDF title: {e}")
            
            logger.info(f"Final: {len(ocr_pages)} pages with OCR, total {len(full_text)} chars")
            
            content_limit = 500000
            result = self.add_entity(
                name=name,
                content=full_text[:content_limit],
                tipo="source",
                fuente=file_path,
                estado="final",
                tags=["pdf", "document", f"pages:{num_pages}"] + (["ocr-assisted"] if ocr_pages else [])
            )
            
            if result.get("success"):
                result["pages_processed"] = num_pages
                result["digital_pages"] = len(pages_with_text)
                result["ocr_pages"] = ocr_pages
                result["has_ocr"] = bool(ocr_pages)
                result["content_length"] = len(full_text)
                result["truncated"] = len(full_text) > content_limit

                quality_info = self.track_ingest_quality("pdf", name, result)
                result["quality_score"] = quality_info["quality_score"]
                result["quality_alerts"] = quality_info.get("alerts", [])

            logger.info(f"PDF ingestion complete: {len(full_text)} chars, {len(ocr_pages)} OCR pages, quality: {result.get('quality_score', 'N/A')}")
            return result
            
        except ImportError as ie:
            logger.error(f"Missing PDF dependency: {ie}. Install pypdf: pip install pypdf")
            return {"error": f"Missing PDF dependency: {ie}"}
        except Exception as e:
            logger.error(f"PDF ingest error: {e}")
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