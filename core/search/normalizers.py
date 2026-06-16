"""Score normalizers for search result fusion.

Normalizes scores from different sources (FAISS, Graphify, BM25)
to a common [0, 1] range for fair comparison and fusion.
"""

from typing import List, Optional


class ScoreNormalizer:
    """Normaliza scores de diferentes fuentes a [0, 1]."""

    @staticmethod
    def min_max_normalize(
        scores: List[float],
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> List[float]:
        if not scores:
            return []

        mn = min_val if min_val is not None else min(scores)
        mx = max_val if max_val is not None else max(scores)

        if mx == mn:
            return [0.5] * len(scores)

        return [(s - mn) / (mx - mn) for s in scores]

    @staticmethod
    def z_score_normalize(scores: List[float]) -> List[float]:
        if not scores:
            return []

        import numpy as np
        arr = np.array(scores)
        mean = arr.mean()
        std = arr.std()

        if std == 0:
            return [0.0] * len(scores)

        return ((arr - mean) / std).tolist()

    @staticmethod
    def rank_based(scores: List[float]) -> List[float]:
        if not scores:
            return []
        n = len(scores)
        return [(n - i) / n for i in range(n)]
