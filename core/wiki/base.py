"""Wiki base module - Database initialization, CRUD, quality tracking, maintenance."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import config

from core.wiki.search import WikiSearchMixin
from core.wiki.ingest import WikiIngestMixin
from core.wiki.obsidian import WikiObsidianMixin

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Generate safe id from name."""
    import re
    s = name.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[-\s]+', '_', s)
    return s[:80]


class Wiki(WikiSearchMixin, WikiIngestMixin, WikiObsidianMixin):
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
        except Exception:
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
        except Exception:
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
            except Exception:
                return []
        return []

    def _save_quality_history(self, history: list):
        """Save quality history to JSON."""
        qf = self._get_quality_file()
        qf.write_text(json.dumps(history[-500:], indent=2, ensure_ascii=False), encoding="utf-8")

    def _calculate_quality_score(self, ingest_type: str, data: dict) -> int:
        """Calculate quality score (0-100) based on ingest type and data."""
        score = 70
        content_len = data.get("content_length", 0)

        if ingest_type == "pdf":
            pages = data.get("pages_processed", 0)
            digital = data.get("digital_pages", 0)
            ocr_pages = len(data.get("ocr_pages", []))

            if pages > 0:
                digital_ratio = digital / pages
                score += int(digital_ratio * 20)
                score += min(int(content_len / 5000), 10)

            if ocr_pages > 0 and data.get("has_ocr"):
                score -= 5

            if content_len < 1000:
                score -= 20

        elif ingest_type == "youtube":
            duration = data.get("duration_seconds", 0)
            transcript_chars = data.get("transcript_chars", 0)

            if duration > 0 and transcript_chars > 0:
                ratio = transcript_chars / duration
                score += min(int(ratio / 10), 25)

            if transcript_chars < 500:
                score -= 25

        elif ingest_type == "url":
            html_len = data.get("html_length", 0)
            if html_len > 0 and content_len > 0:
                ratio = (content_len / html_len) * 100
                score += min(int(ratio), 15)

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
            logger.warning(f"Low quality ingest: {name} (score: {quality_score})")

        return {
            "quality_score": quality_score,
            "is_low_quality": quality_score < 50,
            "alerts": [f"Low quality ingest: {name} (score: {quality_score})"] if quality_score < 50 else []
        }

    def get_ingest_quality(self, limit: int = 20) -> dict:
        """Get quality stats for recent ingests."""
        history = self._load_quality_history()
        recent = history[-limit:] if history else []

        if not recent:
            return {
                "total": 0, "avg_score": 0, "low_quality_count": 0,
                "by_type": {}, "recent": []
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
        except Exception:
            fts5_count = 0

        try:
            self.cursor.execute("SELECT COUNT(*) FROM entities")
            entity_count = self.cursor.fetchone()[0]
        except Exception:
            entity_count = 0

        if fts5_count < entity_count or fts5_count == 0 or fts5_count > entity_count:
            try:
                self.cursor.execute("DROP TABLE IF EXISTS entities_fts")
                self.cursor.execute("CREATE VIRTUAL TABLE entities_fts USING fts5(name, content, tipo, tags)")

                self.cursor.execute("SELECT id, name, content, tipo, tags FROM entities")
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

    STOP_WORDS = {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "en", "que", "es",
        "a", "al", "con", "por", "para", "se", "su", "sus", "lo", "como", "qué", "cuál", "cuáles",
        "donde", "dónde", "cuando", "cuándo", "quien", "quién", "tiene", "son", "está",
        "hacer", "sirve", "servir", "sobre", "entre", "sin", "desde",
        "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "aquel", "aquella",
        "yo", "tú", "él", "ella", "nosotros", "ellos", "ellas", "mi", "tu", "su", "me", "te",
        "nos", "os", "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
        "is", "are", "was", "were", "what", "how", "why", "when", "where", "who", "which",
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

    def close(self):
        """Close database connection."""
        self.conn.close()
