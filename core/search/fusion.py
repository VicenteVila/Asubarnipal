"""Search result fusion methods.

Provides WeightedFusion (weighted average) and ReciprocalRankFusion (RRF)
for combining results from different search systems.
"""

from typing import List, Dict, Any, Optional


class WeightedFusion:
    """Fusión de resultados por promedio ponderado.

    Args:
        w_faiss: Peso para FAISS scores (default 0.6).
        w_graph: Peso para Graphify scores (default 0.4).
    """

    def __init__(self, w_faiss: float = 0.6, w_graph: float = 0.4):
        if abs(w_faiss + w_graph - 1.0) > 1e-6:
            raise ValueError("Los pesos deben sumar 1.0")
        self.w_faiss = w_faiss
        self.w_graph = w_graph

    def fuse(
        self,
        faiss_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        results_dict: Dict[str, Any] = {}

        for r in faiss_results:
            id_ = r.get("id", r.get("name", ""))
            if id_ not in results_dict:
                results_dict[id_] = {
                    "id": id_,
                    "content": r.get("content", ""),
                    "metadata": r.get("metadata", {}),
                    "score_faiss": 0.0,
                    "score_graph": 0.0,
                }
            results_dict[id_]["score_faiss"] = r.get("score", 0.0)

        for r in graph_results:
            id_ = r.get("id", r.get("name", ""))
            if id_ not in results_dict:
                results_dict[id_] = {
                    "id": id_,
                    "content": r.get("content", ""),
                    "metadata": r.get("metadata", {}),
                    "score_faiss": 0.0,
                    "score_graph": 0.0,
                }
            results_dict[id_]["score_graph"] = r.get("score", 0.0)

        for r in results_dict.values():
            r["score_final"] = self.w_faiss * r["score_faiss"] + self.w_graph * r["score_graph"]

        fused = sorted(results_dict.values(), key=lambda x: x["score_final"], reverse=True)
        return fused


class ReciprocalRankFusion:
    """Fusión por Reciprocal Rank Fusion (RRF).

    Args:
        k: Constante RRF (default 60).
    """

    def __init__(self, k: int = 60):
        self.k = k

    def fuse(self, *result_lists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scores_dict: Dict[str, float] = {}
        results_dict: Dict[str, Any] = {}

        for results in result_lists:
            for rank, r in enumerate(results):
                id_ = r.get("id", r.get("name", ""))
                rrf_score = 1.0 / (self.k + rank + 1)

                if id_ not in scores_dict:
                    scores_dict[id_] = 0.0
                    results_dict[id_] = {
                        "id": id_,
                        "content": r.get("content", ""),
                        "metadata": r.get("metadata", {}),
                    }
                scores_dict[id_] += rrf_score

        for id_, score in scores_dict.items():
            results_dict[id_]["score_rrf"] = score

        fused = sorted(results_dict.values(), key=lambda x: x["score_rrf"], reverse=True)
        return fused


def fuse_weighted(
    faiss_results: List[Dict[str, Any]],
    graph_results: List[Dict[str, Any]],
    w_faiss: float = 0.6,
) -> List[Dict[str, Any]]:
    fusor = WeightedFusion(w_faiss=w_faiss, w_graph=1.0 - w_faiss)
    return fusor.fuse(faiss_results, graph_results)


def fuse_rrf(*result_lists: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
    fusor = ReciprocalRankFusion(k=k)
    return fusor.fuse(*result_lists)
