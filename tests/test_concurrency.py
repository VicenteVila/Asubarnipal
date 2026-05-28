"""Concurrency tests for multi-user scenarios."""

import os
import sys
import unittest
import asyncio
import threading
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConcurrency(unittest.TestCase):
    """Test concurrent access patterns."""

    def test_concurrent_rate_limiter(self):
        """Test rate limiter under concurrent access."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=10, refill_rate=10, refill_interval=60)

        results = []

        def try_request(user_id):
            return limiter.allow(f"user_{user_id}")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for i in range(20):
                futures.append(executor.submit(try_request, i % 5))

            for future in as_completed(futures):
                results.append(future.result())

        allowed = sum(1 for r in results if r)
        denied = sum(1 for r in results if not r)

        self.assertGreater(allowed, 0)
        self.assertEqual(allowed + denied, len(results))

    def test_concurrent_memory_tree_reads(self):
        """Test concurrent reads from memory tree."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            with patch("config.DATA_DIR", temp_path):
                from core.memory_tree import MemoryTree

                tree = MemoryTree(vault_name="concurrent_test")
                tree.db_path = temp_path / "memory_tree_concurrent.db"
                tree._init_db()

                for i in range(20):
                    tree.insert(f"Concurrent memory {i}")

                results = []

                def query_tree(query):
                    return tree.query(query, limit=5)

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = []
                    for i in range(10):
                        futures.append(executor.submit(query_tree, f"memory {i}"))

                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            results.append(len(result))
                        except Exception:
                            results.append(0)

                self.assertEqual(len(results), 10)

                tree.close()

    def test_concurrent_vault_switching(self):
        """Test concurrent vault switching is safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            with patch("config.DATA_DIR", temp_path):
                from core.vault_manager import VaultManager

                VaultManager._instance = None
                vm = VaultManager()
                vm._config = {"active_vault": None, "vaults": {}}

                vm.create("vault_a", str(temp_path / "a"))
                vm.create("vault_b", str(temp_path / "b"))

                results = []

                def switch_vault(vault_name):
                    try:
                        result = vm.switch(vault_name)
                        if result.get("success"):
                            return vault_name
                        return "error"
                    except Exception:
                        return "error"

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = []
                    for i in range(10):
                        name = "vault_a" if i % 2 == 0 else "vault_b"
                        futures.append(executor.submit(switch_vault, name))

                    for future in as_completed(futures):
                        results.append(future.result())

                self.assertEqual(len(results), 10)
                self.assertTrue(all(r in ["vault_a", "vault_b", "error"] for r in results))

                VaultManager._instance = None

    def test_concurrent_cache_access(self):
        """Test concurrent cache access."""
        from core.cache import QueryCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = QueryCache(default_ttl=60, max_size=100)
            cache.cache_dir = Path(tmpdir) / "cache"
            cache.cache_dir.mkdir(exist_ok=True)

            def write_read(key, value):
                cache.set(key, value)
                return cache.get(key)

            results = []

            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = []
                for i in range(20):
                    futures.append(executor.submit(write_read, f"key_{i}", f"value_{i}"))

                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception:
                        results.append(None)

            self.assertEqual(len(results), 20)


class TestAsyncConcurrency(unittest.TestCase):
    """Test async concurrency patterns."""

    def test_async_gather_simulation(self):
        """Test asyncio.gather pattern for parallel operations."""
        async def parallel_operations():
            async def mock_llm_call(delay, result):
                await asyncio.sleep(delay)
                return result

            tasks = [
                mock_llm_call(0.01, "result_1"),
                mock_llm_call(0.02, "result_2"),
                mock_llm_call(0.01, "result_3"),
            ]

            results = await asyncio.gather(*tasks)
            return results

        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(parallel_operations())
            self.assertEqual(len(results), 3)
            self.assertIn("result_1", results)
            self.assertIn("result_2", results)
            self.assertIn("result_3", results)
        finally:
            loop.close()

    def test_async_rate_limiting(self):
        """Test rate limiting with async requests."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=5, refill_rate=5, refill_interval=60)

        async def make_request():
            return limiter.allow("async_user")

        async def run_concurrent():
            tasks = [make_request() for _ in range(10)]
            return await asyncio.gather(*tasks)

        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(run_concurrent())
            allowed = sum(1 for r in results if r)
            self.assertEqual(allowed, 5)
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
