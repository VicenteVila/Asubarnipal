"""Individual classifiers for hybrid search ensemble.

Implements BM25, FAISS, Graphify, and Fidelity classifiers
that produce normalized scores [0, 1] for candidate documents.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BM25Classifier:
    """Clasificador basado en BM25 (keyword search)."""

    def __init__(self):
        self.bm25 = None
        self.corpus_ids: List[str] = []

    def fit(self, documents: List[Dict[str, Any]]):
        from rank_bm25 import BM25Okapi

        self.corpus_ids = [d.get("id", d.get("name", str(i))) for i, d in enumerate(documents)]
        tokenized = [d.get("content", "").lower().split() for d in documents]
        self.bm25 = BM25Okapi(tokenized)

    def score(self, query: str, candidates: List[Dict[str, Any]]) -> List[float]:
        if not self.bm25 or not candidates:
            return [0.0] * len(candidates)

        import numpy as np

        tokenized_query = query.lower().split()
        raw_scores = self.bm25.get_scores(tokenized_query)

        max_score = float(np.max(raw_scores)) if len(raw_scores) > 0 and float(np.max(raw_scores)) > 0 else 1.0
        normalized = [float(s) / max_score for s in raw_scores]

        return normalized


class FAISSClassifier:
    """Clasificador basado en FAISS (vector similarity)."""

    def __init__(self, index_path: Optional[str] = None):
        self.index_path = index_path
        self.index = None

    def load(self, index_path: Optional[str] = None):
        import faiss
        path = index_path or self.index_path
        if path:
            self.index = faiss.read_index(path)

    def score(self, query: str, candidates: List[Dict[str, Any]]) -> List[float]:
        if self.index is None:
            return [0.0] * len(candidates)

        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            query_emb = model.encode([query])
            distances, _ = self.index.search(query_emb.astype(np.float32), len(candidates))
            scores = [1.0 / (1.0 + d) for d in distances[0]]
            return scores
        except Exception as e:
            logger.warning(f"FAISSClassifier error: {e}")
            return [0.0] * len(candidates)


class GraphifyClassifier:
    """Clasificador basado en Graphify (graph relationships)."""

    def __init__(self, graph_path: Optional[str] = None):
        self.graph_path = graph_path
        self.graph: Optional[Dict[str, Any]] = None

    def load(self, graph_path: Optional[str] = None):
        import json
        path = graph_path or self.graph_path
        if path:
            with open(path, "r") as f:
                self.graph = json.load(f)

    def score(self, query: str, candidates: List[Dict[str, Any]]) -> List[float]:
        if not self.graph:
            return [0.0] * len(candidates)

        nodes = self.graph.get("nodes", [])
        total_nodes = len(nodes)
        node_map = {n.get("id", n.get("name", "")): n for n in nodes}

        scores = []
        for candidate in candidates:
            node_id = candidate.get("id", candidate.get("name", ""))
            node = node_map.get(node_id)

            if not node:
                scores.append(0.0)
                continue

            connections = len(node.get("edges", node.get("links", [])))
            centrality = connections / (total_nodes - 1) if total_nodes > 1 else 0.0
            score = 0.6 * min(connections / 10.0, 1.0) + 0.4 * centrality
            scores.append(min(score, 1.0))

        return scores


class FidelityClassifier:
    """Clasificador basado en calidad del documento (fallback 0.5 por defecto)."""

    def __init__(self):
        pass

    def score(self, query: str, candidates: List[Dict[str, Any]]) -> List[float]:
        return [0.5] * len(candidates)
