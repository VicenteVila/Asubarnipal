"""Wiki obsidian module - Sync, save to Obsidian, graph updates."""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class WikiObsidianMixin:
    """Mixin class with Obsidian sync, save, and graph update methods."""

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
                    name=md_file.stem, content=content[:20000],
                    tipo=frontmatter.get("tipo", "entity"),
                    fuente=frontmatter.get("fuente", "obsidian"),
                    estado=frontmatter.get("estado", "final"),
                    tags=frontmatter.get("tags", "").split(","),
                )
                imported += 1
            except Exception:
                pass

        return {"imported": imported}

    def save_to_obsidian(self, name: str, content: str, tipo: str = "source",
                         fuente: str = "", tags: Optional[list[str]] = None, relacionados: Optional[list[str]] = None) -> dict[str, Any]:
        """Save an entity as a .md file in the Obsidian wiki folder."""
        import re
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
                               tags: Optional[list[str]] = None, relacionados: Optional[list[str]] = None) -> None:
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
