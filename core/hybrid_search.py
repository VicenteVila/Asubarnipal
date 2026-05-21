"""Hybrid Search - Búsqueda en SQLite + Obsidian vault."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

import config

logger = logging.getLogger(__name__)


class HybridSearch:
    """Búsqueda que combina SQLite y Obsidian vault."""

    def __init__(self, vault_name: Optional[str] = None) -> None:
        self.vault_name = vault_name or self._get_active_vault()
        self.vault_path = None
        if self.vault_name:
            self.vault_path = self._get_vault_path(self.vault_name)

    def _get_active_vault(self) -> Optional[str]:
        """Get active vault name."""
        try:
            from core.vault_manager import get_vault_manager
            vm = get_vault_manager()
            active = vm.get_active()
            return active.get("name") if active else None
        except Exception:
            return None

    def _get_vault_path(self, name: str) -> Optional[Path]:
        """Get vault path by name."""
        try:
            from core.vault_manager import get_vault_manager
            vm = get_vault_manager()
            vaults = vm.list_vaults()
            for v in vaults.get("vaults", []):
                if v["name"] == name:
                    return Path(v["path"])
        except Exception:
            pass
        return None

    def search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Search in both SQLite and Obsidian vault.

        Returns:
            Dict with:
            - sqlite_results: list of results from wiki.db
            - obsidian_results: list of results from .md files
            - combined: merged results with source indicator
        """
        sqlite_results = self._search_sqlite(query, limit * 2)
        obsidian_results = self._search_obsidian(query, limit * 2)

        # Combine results, prioritizing Obsidian content
        combined = []

        # First add Obsidian results
        for r in obsidian_results:
            combined.append({
                **r,
                "source": "obsidian",
                "priority": 1
            })

        # Then add SQLite results
        for r in sqlite_results:
            # Check if this entity already exists from Obsidian
            exists = any(c.get("name") == r.get("name") for c in combined)
            if not exists:
                combined.append({
                    **r,
                    "source": "sqlite",
                    "priority": 2
                })

        # Sort by priority (Obsidian first) then by relevance
        combined.sort(key=lambda x: (x.get("priority", 99), -x.get("score", 0)))

        return {
            "query": query,
            "sqlite_count": len(sqlite_results),
            "obsidian_count": len(obsidian_results),
            "total_count": len(combined),
            "sqlite_results": sqlite_results,
            "obsidian_results": obsidian_results,
            "combined_results": combined[:limit],
            "vault_active": self.vault_name,
            "vault_path": str(self.vault_path) if self.vault_path else None,
        }

    def _search_sqlite(self, query: str, limit: int) -> List[Dict]:
        """Search in SQLite wiki database."""
        try:
            from core.wiki import Wiki
            wiki = Wiki()
            results = wiki.search(query, limit)
            return [
                {
                    "name": r.get("name", ""),
                    "tipo": r.get("tipo", "entity"),
                    "content": r.get("content", "")[:2000],
                    "score": 1.0,
                    "fecha_ingesta": r.get("fecha_ingesta", ""),
                    "fuente": r.get("fuente", ""),
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"SQLite search error: {e}")
            return []

    def _search_obsidian(self, query: str, limit: int) -> List[Dict]:
        """Search in Obsidian vault markdown files."""
        if not self.vault_path or not self.vault_path.exists():
            logger.debug(f"Obsidian vault not accessible: {self.vault_path}")
            return []

        results = []
        query_terms = query.lower().split()
        query_any = " ".join(query_terms)

        try:
            for md_file in self.vault_path.rglob("*.md"):
                if md_file.name.startswith("."):
                    continue
                try:
                    content = md_file.read_text(encoding="utf-8")
                    content_lower = content.lower()

                    match_found = query_any in content_lower or any(
                        term in content_lower for term in query_terms
                    )

                    if match_found:
                        title = md_file.stem
                        if content.startswith("---"):
                            end = content.find("---", 3)
                            if end > 0:
                                fm = content[3:end]
                                for line in fm.split("\n"):
                                    if line.startswith("title:"):
                                        title = line.split(":", 1)[1].strip()
                                        break

                        pos = content_lower.find(query_terms[0] if query_terms else query_any)
                        if pos < 0:
                            pos = 0
                        start = max(0, pos - 150)
                        end = min(len(content), pos + 300)
                        snippet = content[start:end].strip()

                        results.append({
                            "name": title,
                            "path": str(md_file),
                            "content": snippet,
                            "score": 0.9,
                        })

                        if len(results) >= limit * 2:
                            break

                except Exception as e:
                    logger.debug(f"Error reading {md_file}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Obsidian search error: {e}")

        return results[:limit]

    def get_context_for_llm(self, query: str, max_chars: int = 5000, include_last_source: bool = True) -> str:
        """Get combined context from both sources for LLM."""
        context_parts = []
        query_lower = query.lower()
        query_clean = query.lower().strip()

        is_about_last = any(kw in query_lower for kw in [
            "ultimo", "último", "última", "último pdf", "último video",
            "último ingestado", "last", "reciente", "último contenido"
        ])

        if include_last_source and is_about_last:
            wants_pdf = any(kw in query_lower for kw in ["pdf", "documento", "paper", "articulo"])
            wants_video = any(kw in query_lower for kw in ["video", "youtube", "charla", "talk", "presentacion"])

            try:
                from core.wiki import Wiki
                wiki = Wiki()
                last_source = wiki.get_last_source("pdf" if wants_pdf else ("youtube" if wants_video else "all"))
                tipo_label = "PDF" if wants_pdf else ("VIDEO YOUTUBE" if wants_video else "CONTENIDO")

                if last_source and last_source.get("content"):
                    context_parts.append(f"=== ÚLTIMO {tipo_label} INGESTADO ===")
                    context_parts.append(f"Título: {last_source.get('name', 'Sin título')[:100]}")
                    context_parts.append(f"Fecha: {last_source.get('fecha', 'N/A')}")
                    content = last_source.get("content", "")
                    import re
                    plain = re.sub(r'---[\s\S]*?---', '', content)
                    plain = re.sub(r'#+ ', '', plain)
                    plain = plain[:2500]
                    context_parts.append(f"\n=== CONTENIDO ===\n{plain}")
                    return "\n".join(context_parts)
            except Exception as e:
                logger.debug(f"Error getting last source: {e}")

        search_results = self.search(query, limit=20)

        all_candidates = []
        source_entities = []

        for r in search_results.get("obsidian_results", []):
            cand = {
                "name": r.get("name", ""),
                "source": "obsidian",
                "content": r.get("content", ""),
                "path": r.get("path", ""),
                "tipo": "obsidian",
                "original_score": r.get("score", 0.8),
                "fecha_ingesta": None
            }
            all_candidates.append(cand)
            if self._is_keyword_match(query_clean, r.get("name", "")):
                source_entities.append(cand)

        for r in search_results.get("sqlite_results", []):
            cand = {
                "name": r.get("name", ""),
                "source": "sqlite",
                "content": r.get("content", ""),
                "tipo": r.get("tipo", "entity"),
                "original_score": r.get("score", 1.0),
                "fecha_ingesta": r.get("fecha_ingesta"),
                "fuente": r.get("fuente", "")
            }
            all_candidates.append(cand)

            if self._is_keyword_match(query_clean, r.get("name", "")):
                source_entities.append(cand)

        if not all_candidates:
            return "No se encontró información relevante."

        ranked = self._rank_with_scoring(query, all_candidates, source_entities)

        obsidian_top = [r for r in ranked if r.get("source") == "obsidian"]
        sqlite_top = [r for r in ranked if r.get("source") == "sqlite"]

        if obsidian_top:
            context_parts.append("\n=== CONTENIDO DE OBSIDIAN (Vault activa) ===")
            for r in obsidian_top[:5]:
                context_parts.append(f"\n## {r.get('name', 'Sin título')}")
                context_parts.append(f"Fuente: {r.get('path', 'N/A')}")
                context_parts.append(f"Contenido: {r.get('content', '')[:800]}")

        if sqlite_top:
            context_parts.append("\n=== CONTENIDO DE SQLite (Wiki) ===")
            for r in sqlite_top[:5]:
                tipo = r.get("tipo", "entity")
                content_snippet = r.get("content", "")[:800]
                context_parts.append(f"\n## {r.get('name', 'Sin título')}")
                context_parts.append(f"Tipo: {tipo}")
                context_parts.append(f"Contenido: {content_snippet}")

        full_context = "\n".join(context_parts)
        if len(full_context) > max_chars:
            full_context = full_context[:max_chars] + "\n\n[... contenido truncado]"

        return full_context

    def _is_keyword_match(self, query: str, name: str) -> bool:
        """Check if query keywords appear in entity name."""
        query_tokens = query.lower().split()
        name_lower = name.lower()
        for token in query_tokens:
            if len(token) < 2:
                continue
            if token in name_lower or name_lower in token:
                return True
            for keyword in ["lora", "qlora", "transformer", "rag", "agent", "memory", "graph"]:
                if keyword in token and keyword in name_lower:
                    return True
        return False

    def _rank_with_scoring(self, query: str, candidates: list, source_entities: list) -> list:
        """Rank candidates using scoring with fallback."""
        if not candidates:
            return []

        query_lower = query.lower()
        query_tokens = [t.strip() for t in query_lower.split() if len(t.strip()) >= 2]

        type_priority = {"source": 10.0, "pdf": 10.0, "video": 6.0, "concept": 4.0, "entity": 2.0, "obsidian": 3.0}
        fuente_priority = {".pdf": 3.0, "temp": 2.0, ".md": 1.0, "youtube": 0.8}

        scored = []
        for c in candidates:
            score = 0.0
            content = c.get("content", "") or ""
            name = c.get("name", "") or ""

            name_lower = name.lower()
            for token in query_tokens:
                if token in name_lower:
                    score += 20.0
                if len(content) > 50 and token in content.lower():
                    score += 5.0

            tipo = c.get("tipo", "entity").lower()
            score += type_priority.get(tipo, 1.0)

            fuente = c.get("fuente", "") or ""
            for fp, bonus in fuente_priority.items():
                if fp in fuente.lower():
                    score += bonus
                    break

            score += min(len(content) / 10000.0, 5.0)

            fecha = c.get("fecha_ingesta") or ""
            if fecha:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(fecha)
                    days_ago = (datetime.now() - dt).days
                    score += max(0, (30 - days_ago) / 30.0)
                except Exception:
                    pass

            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        ranked = [c for _, c in scored]

        if source_entities:
            ranked = source_entities[:3] + [r for r in ranked if r not in source_entities[:3]]

        return ranked[:10]

    def _rank_with_scoring_fallback(self, query: str, candidates: list) -> list:
        """Fallback ranker when Ollama is unavailable - sort by recent + content_length."""
        if not candidates:
            return []

        scored = []
        for c in candidates:
            score = 0.0
            content = c.get("content", "") or ""
            name = c.get("name", "") or ""
            tipo = c.get("tipo", "entity").lower()

            if tipo == "source":
                score += 100
            elif tipo == "pdf":
                score += 100
            elif tipo == "video":
                score += 50
            elif tipo == "concept":
                score += 20

            score += min(len(content) / 1000.0, 50.0)

            fecha = c.get("fecha_ingesta") or ""
            if fecha:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(fecha)
                    days_ago = (datetime.now() - dt).days
                    score += max(0, (30 - days_ago) / 30.0) * 10
                except Exception:
                    pass

            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:5]]


def get_hybrid_search(vault_name: str = None) -> HybridSearch:
    """Get HybridSearch instance."""
    return HybridSearch(vault_name)