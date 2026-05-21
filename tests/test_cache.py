"""Tests for core/cache.py."""

import json
import time
import unittest
from pathlib import Path
from unittest.mock import patch


class TestQueryCache(unittest.TestCase):
    """Test file-based query cache."""

    def setUp(self):
        import tempfile
        import importlib
        import core.cache
        core.cache._cache = None
        importlib.reload(core.cache)
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        import core.cache
        core.cache._cache = None
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_cache_miss_returns_none(self):
        from core.cache import QueryCache

        cache = QueryCache(cache_dir=self.test_dir)
        result = cache.get("nonexistent query")
        self.assertIsNone(result)

    def test_cache_set_and_get(self):
        from core.cache import QueryCache

        cache = QueryCache(cache_dir=self.test_dir)
        cache.set("test query", {"answer": "42"})

        result = cache.get("test query")
        self.assertEqual(result, {"answer": "42"})

    def test_cache_with_params(self):
        from core.cache import QueryCache

        cache = QueryCache(cache_dir=self.test_dir)
        cache.set("query", "result1", params={"mode": "wiki"})
        cache.set("query", "result2", params={"mode": "vectorial"})

        self.assertEqual(cache.get("query", params={"mode": "wiki"}), "result1")
        self.assertEqual(cache.get("query", params={"mode": "vectorial"}), "result2")

    def test_cache_ttl_expiry(self):
        from core.cache import QueryCache

        cache = QueryCache(cache_dir=self.test_dir, default_ttl=1)
        cache.set("query", "result")

        time.sleep(1.1)

        result = cache.get("query")
        self.assertIsNone(result)

    def test_cache_invalidate(self):
        from core.cache import QueryCache

        cache = QueryCache(cache_dir=self.test_dir)
        cache.set("query", "result")
        self.assertIsNotNone(cache.get("query"))

        cache.invalidate("query")
        self.assertIsNone(cache.get("query"))

    def test_cache_clear(self):
        from core.cache import QueryCache

        cache = QueryCache(cache_dir=self.test_dir)
        cache.set("q1", "r1")
        cache.set("q2", "r2")
        cache.set("q3", "r3")

        count = cache.clear()
        self.assertEqual(count, 3)
        self.assertEqual(cache.stats()["entries"], 0)

    def test_cache_eviction(self):
        from core.cache import QueryCache

        cache = QueryCache(cache_dir=self.test_dir, max_size=3)
        cache.set("q1", "r1")
        cache.set("q2", "r2")
        cache.set("q3", "r3")
        cache.set("q4", "r4")

        stats = cache.stats()
        self.assertEqual(stats["entries"], 3)

    def test_cache_stats(self):
        from core.cache import QueryCache

        cache = QueryCache(cache_dir=self.test_dir, default_ttl=3600, max_size=500)
        cache.set("test", "data")

        stats = cache.stats()
        self.assertEqual(stats["entries"], 1)
        self.assertEqual(stats["default_ttl"], 3600)
        self.assertEqual(stats["max_size"], 500)
        self.assertGreater(stats["total_size_bytes"], 0)

    def test_get_cache_singleton(self):
        from core.cache import get_cache

        cache1 = get_cache()
        cache2 = get_cache()
        self.assertIs(cache1, cache2)


if __name__ == "__main__":
    unittest.main()
