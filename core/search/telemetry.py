"""Search telemetry - Track and analyze search performance metrics.

Records latency, result counts, scores, and per-classifier timing
for every search query. Provides aggregated statistics and export.
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchMetric:
    timestamp: str = ""
    query: str = ""
    num_results: int = 0
    avg_score: float = 0.0
    max_score: float = 0.0
    min_score: float = 0.0
    timing: Dict[str, float] = field(default_factory=dict)
    method: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "query": self.query[:100],
            "num_results": self.num_results,
            "avg_score": round(self.avg_score, 4),
            "max_score": round(self.max_score, 4),
            "min_score": round(self.min_score, 4),
            "timing": {k: round(v, 2) for k, v in self.timing.items()},
            "method": self.method,
        }


@dataclass
class SearchStats:
    total_queries: int = 0
    avg_latency_ms: float = 0.0
    avg_results_per_query: float = 0.0
    avg_score: float = 0.0
    p95_latency_ms: float = 0.0
    p95_results: float = 0.0
    by_method: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "avg_results_per_query": round(self.avg_results_per_query, 1),
            "avg_score": round(self.avg_score, 4),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p95_results": round(self.p95_results, 1),
            "by_method": self.by_method,
        }


class SearchTelemetry:
    """Telemetría detallada de búsquedas."""

    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.metrics: List[SearchMetric] = []

    def record(
        self,
        query: str,
        results: List[Any],
        timing: Dict[str, float],
        method: str = "hybrid",
    ):
        scores = [r.get("score_ensemble", r.get("score_final", r.get("score", 0))) for r in results]

        metric = SearchMetric(
            timestamp=datetime.now().isoformat(),
            query=query,
            num_results=len(results),
            avg_score=sum(scores) / len(scores) if scores else 0.0,
            max_score=max(scores) if scores else 0.0,
            min_score=min(scores) if scores else 0.0,
            timing=timing,
            method=method,
        )

        self.metrics.append(metric)

        if len(self.metrics) > self.max_records:
            self.metrics = self.metrics[-self.max_records:]

    def get_stats(self) -> SearchStats:
        if not self.metrics:
            return SearchStats()

        latencies = [m.timing.get("total_ms", m.timing.get("total", 0)) for m in self.metrics]
        results_counts = [m.num_results for m in self.metrics]
        avg_scores = [m.avg_score for m in self.metrics]

        by_method: Dict[str, int] = {}
        for m in self.metrics:
            by_method[m.method] = by_method.get(m.method, 0) + 1

        return SearchStats(
            total_queries=len(self.metrics),
            avg_latency_ms=float(np.mean(latencies)),
            avg_results_per_query=float(np.mean(results_counts)),
            avg_score=float(np.mean(avg_scores)),
            p95_latency_ms=float(np.percentile(latencies, 95)),
            p95_results=float(np.percentile(results_counts, 95)),
            by_method=by_method,
        )

    def export(self, path: str):
        data = [m.to_dict() for m in self.metrics]
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))
        logger.info(f"Exported {len(data)} search metrics to {path}")

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self.metrics[-n:]]

    def clear(self):
        self.metrics.clear()
        logger.info("Search telemetry cleared")


_telemetry_instance: Optional[SearchTelemetry] = None


def get_telemetry() -> SearchTelemetry:
    global _telemetry_instance
    if _telemetry_instance is None:
        _telemetry_instance = SearchTelemetry()
    return _telemetry_instance
