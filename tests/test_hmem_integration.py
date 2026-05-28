"""Integration tests for H-Mem: remember → consolidate → retrieve → think → answer."""

import os
import sys
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHMemIntegration(unittest.TestCase):
    """Test H-Mem system end-to-end."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_memory_tree_insert_and_query(self):
        """Test inserting memories and querying them."""
        db_path = self.temp_path / "memory_tree_test.db"

        with patch("config.DATA_DIR", self.temp_path):
            from core.memory_tree import MemoryTree

            tree = MemoryTree(vault_name="test_hmem")
            tree.db_path = db_path
            tree._init_db()

            node = tree.insert("First test memory about AI agents")
            self.assertIsNotNone(node)
            self.assertIn("node_id", node)
            self.assertEqual(node["level"], 0)

            node2 = tree.insert("Second memory about RAG systems")
            self.assertIsNotNone(node2)

            stats = tree.get_stats()
            self.assertEqual(stats["total_nodes"], 2)

            tree.close()

    def test_memory_tree_consolidation(self):
        """Test memory consolidation propagates up the tree."""
        with patch("config.DATA_DIR", self.temp_path):
            from core.memory_tree import MemoryTree

            tree = MemoryTree(vault_name="test_consolidation")
            tree.db_path = self.temp_path / "memory_tree_consolidation.db"
            tree._init_db()

            with patch.object(tree, "_compute_similarity", return_value=0.3):
                with patch.object(tree, "_generate_summary", return_value="Consolidated summary"):
                    for i in range(5):
                        tree.insert(f"Memory fragment {i} about topic X")

                    stats = tree.get_stats()
                    self.assertGreater(stats["total_nodes"], 0)

            tree.close()

    def test_memory_tree_temporal_query(self):
        """Test querying with time range filters."""
        with patch("config.DATA_DIR", self.temp_path):
            from core.memory_tree import MemoryTree

            tree = MemoryTree(vault_name="test_temporal")
            tree.db_path = self.temp_path / "memory_tree_temporal.db"
            tree._init_db()

            now = datetime.now()
            tree.insert("Recent memory", timestamp=(now - timedelta(hours=1)).isoformat())
            tree.insert("Older memory", timestamp=(now - timedelta(days=30)).isoformat())

            recent_results = tree.query(
                "memory",
                time_range=(
                    (now - timedelta(days=7)).isoformat(),
                    now.isoformat()
                ),
                scope="short",
            )

            self.assertIsInstance(recent_results, list)

            tree.close()

    def test_memory_tree_get_recent(self):
        """Test getting recent memories."""
        with patch("config.DATA_DIR", self.temp_path):
            from core.memory_tree import MemoryTree

            tree = MemoryTree(vault_name="test_recent")
            tree.db_path = self.temp_path / "memory_tree_recent.db"
            tree._init_db()

            for i in range(10):
                tree.insert(f"Recent memory {i}")

            recent = tree.get_recent(limit=5)
            self.assertEqual(len(recent), 5)

            level0 = tree.get_recent(limit=5, level=0)
            self.assertTrue(all(n["level"] == 0 for n in level0))

            tree.close()

    def test_memory_robustness_calculation(self):
        """Test Ebbinghaus-based robustness scoring."""
        with patch("config.DATA_DIR", self.temp_path):
            from core.memory_tree import MemoryTree

            tree = MemoryTree(vault_name="test_robustness")
            tree.db_path = self.temp_path / "memory_tree_robustness.db"
            tree._init_db()

            node = {
                "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
                "last_consolidation": (datetime.now() - timedelta(days=1)).isoformat(),
                "consolidation_count": 0,
            }

            robustness = tree._memory_robustness(node)
            self.assertGreaterEqual(robustness, 0.0)
            self.assertLessEqual(robustness, 1.0)

            node_high = {
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "last_consolidation": (datetime.now() - timedelta(hours=1)).isoformat(),
                "consolidation_count": 5,
            }

            robustness_high = tree._memory_robustness(node_high)
            self.assertGreater(robustness_high, robustness)

            tree.close()


class TestHMemManagerIntegration(unittest.TestCase):
    """Test HMemManager high-level operations."""

    def setUp(self):
        from core.hybrid_retriever import HMemManager
        HMemManager._instance = None
        HMemManager._initialized = False

    def tearDown(self):
        from core.hybrid_retriever import HMemManager
        HMemManager._instance = None
        HMemManager._initialized = False

    @patch("config.DATA_DIR", new_callable=lambda: Path("/tmp"))
    def test_hmem_manager_singleton(self, mock_data_dir):
        """Test HMemManager singleton pattern."""
        with patch("core.hybrid_retriever.HybridRetriever"):
            from core.hybrid_retriever import HMemManager

            manager1 = HMemManager(vault_name="test")
            manager2 = HMemManager(vault_name="test")

            self.assertIs(manager1, manager2)

    @patch("config.DATA_DIR", new_callable=lambda: Path("/tmp"))
    def test_hmem_remember_and_recall(self, mock_data_dir):
        """Test remember and recall operations."""
        with patch("core.hybrid_retriever.HybridRetriever") as mock_retriever_class:
            mock_retriever = Mock()
            mock_retriever.ingest_memory.return_value = {
                "tree_node_id": "node_0_2024_123456",
                "tree_level": 0,
                "graph_ingest": {"entities_extracted": 2},
            }
            mock_retriever.retrieve.return_value = {
                "plan": {"sub_queries": [], "temporal_hints": [], "focus": "test"},
                "tree_results": [],
                "graph_entities": [],
                "ranked_evidence": [],
                "query_time": datetime.now().isoformat(),
            }
            mock_retriever_class.return_value = mock_retriever

            from core.hybrid_retriever import HMemManager

            manager = HMemManager(vault_name="test")
            manager.retriever = mock_retriever

            result = manager.remember("Test memory content", {"source": "test"})
            self.assertIn("tree_node_id", result)

            recall = manager.recall("test query")
            self.assertIn("query_time", recall)


if __name__ == "__main__":
    unittest.main(verbosity=2)
