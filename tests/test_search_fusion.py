"""Tests for Phase 3 hybrid search modules."""

import pytest
from core.search.normalizers import ScoreNormalizer
from core.search.fusion import WeightedFusion, ReciprocalRankFusion, fuse_weighted, fuse_rrf
from core.search.classifiers import BM25Classifier, GraphifyClassifier, FidelityClassifier
from core.search.ensemble import EnsembleClassifier, EnsembleResult
from core.search.telemetry import SearchTelemetry, SearchStats, SearchMetric, get_telemetry


class TestScoreNormalizer:
    def test_min_max_empty(self):
        assert ScoreNormalizer.min_max_normalize([]) == []

    def test_min_max_single_value(self):
        result = ScoreNormalizer.min_max_normalize([5.0])
        assert result == [0.5]

    def test_min_max_basic(self):
        result = ScoreNormalizer.min_max_normalize([0.0, 5.0, 10.0])
        assert result == [0.0, 0.5, 1.0]

    def test_min_max_all_equal(self):
        result = ScoreNormalizer.min_max_normalize([3.0, 3.0, 3.0])
        assert result == [0.5, 0.5, 0.5]

    def test_min_max_custom_range(self):
        result = ScoreNormalizer.min_max_normalize([2.0, 4.0, 6.0], min_val=0, max_val=10)
        assert result == [0.2, 0.4, 0.6]

    def test_z_score_empty(self):
        assert ScoreNormalizer.z_score_normalize([]) == []

    def test_z_score_single(self):
        result = ScoreNormalizer.z_score_normalize([5.0])
        assert result == [0.0]

    def test_z_score_basic(self):
        result = ScoreNormalizer.z_score_normalize([1.0, 2.0, 3.0])
        assert len(result) == 3
        assert abs(sum(result)) < 1e-10

    def test_rank_based_basic(self):
        result = ScoreNormalizer.rank_based([10, 5, 1])
        assert result == [1.0, 2/3, 1/3]


class TestWeightedFusion:
    def test_fuse_empty(self):
        fusor = WeightedFusion(0.6, 0.4)
        result = fusor.fuse([], [])
        assert result == []

    def test_fuse_basic(self):
        fusor = WeightedFusion(0.6, 0.4)
        faiss = [{"id": "a", "score": 1.0, "content": "doc a"}]
        graph = [{"id": "b", "score": 0.8, "content": "doc b"}]
        result = fusor.fuse(faiss, graph)
        assert len(result) == 2

    def test_fuse_overlap(self):
        fusor = WeightedFusion(0.5, 0.5)
        faiss = [{"id": "a", "score": 1.0}, {"id": "b", "score": 0.5}]
        graph = [{"id": "a", "score": 0.6}, {"id": "c", "score": 0.9}]
        result = fusor.fuse(faiss, graph)
        ids = [r["id"] for r in result]
        assert "a" in ids
        assert "b" in ids
        assert "c" in ids
        a_result = [r for r in result if r["id"] == "a"][0]
        assert a_result["score_final"] == 0.5 * 1.0 + 0.5 * 0.6

    def test_invalid_weights(self):
        with pytest.raises(ValueError):
            WeightedFusion(1.0, 1.0)

    def test_fuse_by_name(self):
        fusor = WeightedFusion(0.7, 0.3)
        faiss = [{"name": "x", "score": 0.9}]
        graph = [{"name": "y", "score": 0.7}]
        result = fusor.fuse(faiss, graph)
        assert len(result) == 2


class TestReciprocalRankFusion:
    def test_fuse_empty(self):
        rrf = ReciprocalRankFusion(k=60)
        assert rrf.fuse([], []) == []

    def test_fuse_single_list(self):
        rrf = ReciprocalRankFusion(k=60)
        results = [{"id": "a", "content": "doc a"}, {"id": "b", "content": "doc b"}]
        fused = rrf.fuse(results)
        assert len(fused) == 2
        assert fused[0]["score_rrf"] > fused[1]["score_rrf"]

    def test_fuse_multiple_lists(self):
        rrf = ReciprocalRankFusion(k=60)
        list1 = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        list2 = [{"id": "c"}, {"id": "a"}, {"id": "d"}]
        fused = rrf.fuse(list1, list2)
        assert len(fused) == 4

    def test_rrf_common_items_ranked_higher(self):
        rrf = ReciprocalRankFusion(k=60)
        list1 = [{"id": "a"}, {"id": "b"}]
        list2 = [{"id": "a"}, {"id": "c"}]
        fused = rrf.fuse(list1, list2)
        assert fused[0]["id"] == "a"

    def test_fuse_with_name_field(self):
        rrf = ReciprocalRankFusion(k=60)
        results = [{"name": "doc1"}]
        fused = rrf.fuse(results)
        assert len(fused) == 1


class TestConvenienceFunctions:
    def test_fuse_weighted(self):
        result = fuse_weighted(
            [{"id": "a", "score": 1.0}],
            [{"id": "b", "score": 0.5}],
            w_faiss=0.6,
        )
        assert len(result) == 2

    def test_fuse_rrf(self):
        result = fuse_rrf(
            [{"id": "a"}],
            [{"id": "b"}],
            k=60,
        )
        assert len(result) == 2


class TestBM25Classifier:
    def test_score_before_fit(self):
        bm25 = BM25Classifier()
        scores = bm25.score("test", [{"id": "1", "content": "test doc"}])
        assert scores == [0.0]

    def test_fit_and_score(self):
        bm25 = BM25Classifier()
        docs = [
            {"id": "1", "content": "python rules the world"},
            {"id": "2", "content": "java runs on servers"},
            {"id": "3", "content": "ruby is elegant"},
        ]
        bm25.fit(docs)
        scores = bm25.score("python rules", docs)
        assert scores[0] > scores[1]
        assert scores[0] > scores[2]

    def test_score_empty_candidates(self):
        bm25 = BM25Classifier()
        bm25.fit([{"id": "1", "content": "test"}])
        assert bm25.score("test", []) == []


class TestGraphifyClassifier:
    def test_score_no_graph(self):
        gc = GraphifyClassifier()
        scores = gc.score("test", [{"id": "a"}])
        assert scores == [0.0]

    def test_score_with_graph(self, tmp_path):
        import json
        graph_path = tmp_path / "graph.json"
        graph = {
            "nodes": [
                {"id": "a", "edges": ["b", "c"]},
                {"id": "b", "edges": ["a"]},
                {"id": "c", "edges": []},
            ]
        }
        graph_path.write_text(json.dumps(graph))
        gc = GraphifyClassifier(str(graph_path))
        gc.load()
        scores = gc.score("test", [{"id": "a"}, {"id": "c"}, {"id": "x"}])
        assert len(scores) == 3
        assert scores[0] > scores[1]

    def test_graph_with_links_field(self, tmp_path):
        import json
        graph_path = tmp_path / "graph.json"
        graph = {"nodes": [{"name": "a", "links": ["b"]}, {"name": "b", "links": []}]}
        graph_path.write_text(json.dumps(graph))
        gc = GraphifyClassifier(str(graph_path))
        gc.load()
        scores = gc.score("test", [{"name": "a"}, {"name": "b"}])
        assert len(scores) == 2
        assert scores[0] >= scores[1]


class TestFidelityClassifier:
    def test_score_returns_list(self):
        fc = FidelityClassifier()
        scores = fc.score("test", [{"id": "a", "content": "test"}])
        assert len(scores) == 1
        assert 0 <= scores[0] <= 1


class TestEnsembleClassifier:
    def test_classify_empty(self):
        ensemble = EnsembleClassifier(use_faiss=False, use_graphify=False, use_fidelity=False)
        assert ensemble.classify("test", []) == []

    def test_classify_basic(self):
        ensemble = EnsembleClassifier(
            use_faiss=False, use_graphify=False, use_fidelity=False,
            weights={"bm25": 1.0},
        )
        docs = [{"id": "1", "content": "test document one"}, {"id": "2", "content": "something else"}]
        ensemble.fit_bm25(docs)
        results = ensemble.classify("test", docs)
        assert len(results) == 2
        assert isinstance(results[0], EnsembleResult)
        assert results[0].score_ensemble >= 0

    def test_weights_auto_normalize(self):
        ensemble = EnsembleClassifier(
            use_faiss=False, use_graphify=False, use_fidelity=False,
            weights={"bm25": 1.0, "fidelity": 1.0},
        )
        w = ensemble.get_weights()
        assert abs(sum(w.values()) - 1.0) < 1e-6

    def test_set_weights(self):
        ensemble = EnsembleClassifier(use_faiss=False, use_graphify=False, use_fidelity=False)
        ensemble.set_weights({"bm25": 0.5, "fidelity": 0.5})
        assert ensemble.get_weights()["bm25"] == 0.5

    def test_results_ordered_by_score(self):
        ensemble = EnsembleClassifier(
            use_faiss=False, use_graphify=False, use_fidelity=False,
            weights={"bm25": 1.0},
        )
        docs = [{"id": "1", "content": "python programming language"}, {"id": "2", "content": "java programming"}]
        ensemble.fit_bm25(docs)
        results = ensemble.classify("python", docs)
        assert results[0].score_ensemble >= results[1].score_ensemble

    def test_to_dict(self):
        result = EnsembleResult(id="a", content="test", score_ensemble=0.85, scores_individual={"bm25": 0.85})
        d = result.to_dict()
        assert d["id"] == "a"
        assert d["score_ensemble"] == 0.85


class TestSearchTelemetry:
    def test_initial_stats_empty(self):
        telemetry = SearchTelemetry()
        stats = telemetry.get_stats()
        assert stats.total_queries == 0

    def test_record_and_stats(self):
        telemetry = SearchTelemetry()
        telemetry.record(
            query="test query",
            results=[{"score_ensemble": 0.8}, {"score_ensemble": 0.6}],
            timing={"total_ms": 150.0, "faiss_ms": 50.0},
            method="hybrid",
        )
        stats = telemetry.get_stats()
        assert stats.total_queries == 1
        assert stats.avg_results_per_query == 2
        assert stats.avg_score == 0.7

    def test_record_with_score_final_fallback(self):
        telemetry = SearchTelemetry()
        telemetry.record("query", [{"score": 0.5}], {"total_ms": 100.0})
        stats = telemetry.get_stats()
        assert stats.total_queries == 1

    def test_export_and_get_recent(self, tmp_path):
        telemetry = SearchTelemetry()
        telemetry.record("q1", [{"score_ensemble": 0.9}], {"total_ms": 100})
        telemetry.record("q2", [{"score_ensemble": 0.7}], {"total_ms": 200})
        recent = telemetry.get_recent(1)
        assert len(recent) == 1
        export_path = str(tmp_path / "search_metrics.json")
        telemetry.export(export_path)
        import json
        data = json.loads(Path(export_path).read_text())
        assert len(data) == 2

    def test_clear(self):
        telemetry = SearchTelemetry()
        telemetry.record("test", [], {"total_ms": 0})
        telemetry.clear()
        assert len(telemetry.metrics) == 0

    def test_max_records(self):
        telemetry = SearchTelemetry(max_records=5)
        for i in range(10):
            telemetry.record(f"q{i}", [{"score_ensemble": 0.5}], {"total_ms": 100})
        assert len(telemetry.metrics) == 5

    def test_get_telemetry_singleton(self):
        t1 = get_telemetry()
        t2 = get_telemetry()
        assert t1 is t2

    def test_by_method_in_stats(self):
        telemetry = SearchTelemetry()
        telemetry.record("q", [], {"total_ms": 0}, method="hybrid")
        stats = telemetry.get_stats()
        assert stats.by_method.get("hybrid") == 1

    def test_search_stats_to_dict(self):
        stats = SearchStats(total_queries=10, avg_latency_ms=150.0)
        d = stats.to_dict()
        assert d["total_queries"] == 10


from pathlib import Path
