"""SearchService - unified search combining RAG + hybrid + ensemble."""

import logging
import time
from typing import Any, Optional

from core.search.ensemble import EnsembleClassifier, EnsembleResult
from core.search.telemetry import get_telemetry

logger = logging.getLogger(__name__)


class SearchService:
    """Unified search that combines RAG, SQLite, Obsidian, and ensemble re-ranking."""

    def __init__(self, use_faiss: bool = False, use_graphify: bool = False, use_fidelity: bool = False):
        self.use_faiss = use_faiss
        self.use_graphify = use_graphify
        self.use_fidelity = use_fidelity
        self._rag = None
        self._hs = None
        self._ensemble: Optional[EnsembleClassifier] = None

    def _get_rag(self):
        if self._rag is None:
            try:
                from index.rag import RAGEngine
                self._rag = RAGEngine()
            except Exception as e:
                logger.warning(f"RAGEngine unavailable: {e}")
        return self._rag

    def _get_hybrid(self, vault_name: str | None = None):
        try:
            from core.hybrid_search import HybridSearch
            return HybridSearch(vault_name=vault_name)
        except Exception as e:
            logger.warning(f"HybridSearch unavailable: {e}")
        return None

    def search(
        self,
        query: str,
        top_k: int = 10,
        include_rag: bool = True,
        include_hybrid: bool = True,
        vault_name: str | None = None,
    ) -> list[EnsembleResult]:
        """
        Search across all available sources with ensemble re-ranking.

        Args:
            query: Search query
            top_k: Max results to return
            include_rag: Whether to search via RAG (FAISS + BM25)
            include_hybrid: Whether to search via hybrid (SQLite + Obsidian)
            vault_name: Optional specific vault to search

        Returns:
            List of EnsembleResult sorted by ensemble score
        """
        t0 = time.perf_counter()
        all_candidates: list[dict[str, Any]] = []

        if include_rag:
            rag = self._get_rag()
            if rag:
                try:
                    rag_results = rag.search(query, top_k=top_k * 2)
                    for r in rag_results:
                        all_candidates.append({
                            "id": r.get("document", r.get("source", "rag:unknown")),
                            "content": r.get("chunk", r.get("content", "")),
                            "metadata": {"source_type": "rag", "score_original": r.get("combined_score", 0)},
                        })
                except Exception as e:
                    logger.warning(f"RAG search error: {e}")

        if include_hybrid:
            hs = self._get_hybrid(vault_name)
            if hs:
                try:
                    hs_results = hs.search(query, limit=top_k * 2)
                    for r in hs_results.get("combined_results", []):
                        all_candidates.append({
                            "id": r.get("name", "hybrid:unknown"),
                            "content": r.get("content", ""),
                            "metadata": {"source_type": r.get("source", "hybrid"), "vault": r.get("vault_active", "")},
                        })
                except Exception as e:
                    logger.warning(f"Hybrid search error: {e}")

        if not all_candidates:
            return []

        ensemble = EnsembleClassifier(
            use_faiss=self.use_faiss,
            use_graphify=self.use_graphify,
            use_fidelity=self.use_fidelity,
        )
        ensemble.fit_bm25(all_candidates)
        results = ensemble.classify(query, all_candidates)
        self._ensemble = ensemble

        elapsed = (time.perf_counter() - t0) * 1000
        get_telemetry().record(
            query=query,
            results=[r.to_dict() for r in results],
            timing={"total_ms": elapsed},
            method="search_service",
        )

        return results[:top_k]

    def search_rag(self, query: str, top_k: int = 5) -> list[EnsembleResult]:
        """Search only via RAG + ensemble."""
        return self.search(query, top_k=top_k, include_rag=True, include_hybrid=False)

    def search_hybrid(self, query: str, top_k: int = 5, vault_name: str | None = None) -> list[EnsembleResult]:
        """Search only via hybrid (SQLite + Obsidian) + ensemble."""
        return self.search(query, top_k=top_k, include_rag=False, include_hybrid=True, vault_name=vault_name)

    def search_combined(self, query: str, top_k: int = 10, vault_name: str | None = None) -> list[EnsembleResult]:
        """Search both RAG and hybrid, combined with ensemble."""
        return self.search(query, top_k=top_k, include_rag=True, include_hybrid=True, vault_name=vault_name)

    def get_stats(self) -> dict[str, Any]:
        """Get search telemetry stats."""
        return get_telemetry().get_stats().to_dict()


_search_service: SearchService | None = None


def get_search_service() -> SearchService:
    """Singleton accessor for SearchService."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
