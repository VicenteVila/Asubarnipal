"""Ensemble classifier for hybrid search.

Combines BM25, FAISS, Graphify, and Fidelity classifiers
with configurable weights for improved search precision.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List

from core.search.classifiers import (
    BM25Classifier,
    FAISSClassifier,
    FidelityClassifier,
    GraphifyClassifier,
)

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS: dict[str, float] = {
    "bm25": 0.2,
    "faiss": 0.4,
    "graphify": 0.3,
    "fidelity": 0.1,
}


@dataclass
class EnsembleResult:
    id: str
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    score_ensemble: float = 0.0
    scores_individual: dict[str, float] = field(default_factory=dict)
    timing_ms: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content[:500],
            "metadata": self.metadata,
            "score_ensemble": round(self.score_ensemble, 4),
            "scores_individual": {k: round(v, 4) for k, v in self.scores_individual.items()},
            "timing_ms": {k: round(v, 2) for k, v in self.timing_ms.items()},
        }


class EnsembleClassifier:
    """Ensemble de clasificadores para búsqueda híbrida."""

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        faiss_index_path: Optional[str] = None,
        graph_path: Optional[str] = None,
        ground_truth: Optional[str] = None,
        use_bm25: bool = True,
        use_faiss: bool = True,
        use_graphify: bool = True,
        use_fidelity: bool = True,
    ):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            self.weights = {k: v / total for k, v in self.weights.items()}

        self.classifiers: Dict[str, Any] = {}

        if use_bm25:
            self.classifiers["bm25"] = BM25Classifier()
        if use_faiss:
            self.classifiers["faiss"] = FAISSClassifier(faiss_index_path)
        if use_graphify:
            self.classifiers["graphify"] = GraphifyClassifier(graph_path)
        if use_fidelity:
            self.classifiers["fidelity"] = FidelityClassifier(ground_truth=ground_truth)

    def fit_bm25(self, documents: list[dict[str, Any]]):
        if "bm25" in self.classifiers:
            self.classifiers["bm25"].fit(documents)

    def load_indexes(self, faiss_index_path: str | None = None, graph_path: str | None = None):
        if "faiss" in self.classifiers:
            self.classifiers["faiss"].load(faiss_index_path)
        if "graphify" in self.classifiers:
            self.classifiers["graphify"].load(graph_path)

    def classify(self, query: str, candidates: list[dict[str, Any]]) -> list[EnsembleResult]:
        if not candidates:
            return []

        scores: dict[str, list[float]] = {}
        timings: dict[str, float] = {}

        for name, classifier in self.classifiers.items():
            t0 = time.perf_counter()
            scores[name] = classifier.score(query, candidates)
            timings[name] = (time.perf_counter() - t0) * 1000

        results: list[EnsembleResult] = []
        for i, candidate in enumerate(candidates):
            ensemble_score = 0.0
            individual_scores: dict[str, float] = {}

            for name in self.classifiers:
                s = scores[name][i] if i < len(scores[name]) else 0.0
                ensemble_score += self.weights.get(name, 0) * s
                individual_scores[name] = s

            results.append(EnsembleResult(
                id=candidate.get("id", candidate.get("name", str(i))),
                content=candidate.get("content", ""),
                metadata=candidate.get("metadata", {}),
                score_ensemble=ensemble_score,
                scores_individual=individual_scores,
                timing_ms=timings,
            ))

        results.sort(key=lambda r: r.score_ensemble, reverse=True)
        return results

    def get_weights(self) -> dict[str, float]:
        return dict(self.weights)

    def set_weights(self, weights: dict[str, float]):
        total = sum(weights.values())
        self.weights = {k: v / total for k, v in weights.items()}
