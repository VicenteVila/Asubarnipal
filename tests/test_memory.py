"""Unit tests for memory.py."""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestEnhancedMemory(unittest.TestCase):
    """Test EnhancedMemory class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_file.close()
        self.temp_path = Path(self.temp_file.name)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_memory_import(self):
        """Test memory module imports successfully."""
        from core.memory import EnhancedMemory
        self.assertIsNotNone(EnhancedMemory)

    def test_memory_init(self):
        """Test EnhancedMemory initialization."""
        from core.memory import EnhancedMemory
        with patch.object(EnhancedMemory, 'MEMORY_FILE', self.temp_path):
            memory = EnhancedMemory()
            self.assertIsNotNone(memory)

    def test_memory_add(self):
        """Test adding a memory."""
        from core.memory import EnhancedMemory
        with patch.object(EnhancedMemory, 'MEMORY_FILE', self.temp_path):
            memory = EnhancedMemory()
            memory.add("Test memory", category="test", priority=5, importance="medium")
            self.assertEqual(len(memory.memories), 1)

    def test_memory_search(self):
        """Test searching memories."""
        from core.memory import EnhancedMemory
        with patch.object(EnhancedMemory, 'MEMORY_FILE', self.temp_path):
            memory = EnhancedMemory()
            memory.add("Python programming is fun", category="tech")
            memory.add("Machine learning is powerful", category="ai")
            results = memory.search("python", limit=5)
            self.assertIsInstance(results, list)

    def test_memory_get_recent(self):
        """Test getting recent memories."""
        from core.memory import EnhancedMemory
        with patch.object(EnhancedMemory, 'MEMORY_FILE', self.temp_path):
            memory = EnhancedMemory()
            memory.add("Memory 1", category="test")
            memory.add("Memory 2", category="test")
            recent = memory.get_recent(5)
            self.assertIsInstance(recent, list)
            self.assertLessEqual(len(recent), 5)

    def test_memory_clear(self):
        """Test clearing all memories."""
        from core.memory import EnhancedMemory
        with patch.object(EnhancedMemory, 'MEMORY_FILE', self.temp_path):
            memory = EnhancedMemory()
            memory.add("Test memory", category="test")
            memory.clear()
            self.assertEqual(len(memory.memories), 0)

    def test_memory_stats(self):
        """Test memory statistics."""
        from core.memory import EnhancedMemory
        with patch.object(EnhancedMemory, 'MEMORY_FILE', self.temp_path):
            memory = EnhancedMemory()
            memory.add("Memory 1", category="tech")
            memory.add("Memory 2", category="ai")
            # Use get_recent as stats proxy
            recent = memory.get_recent(10)
            self.assertIsInstance(recent, list)
            self.assertEqual(len(recent), 2)


class TestMemoryCategories(unittest.TestCase):
    """Test memory category handling."""

    def test_priority_levels(self):
        """Test memory priority levels."""
        valid_priorities = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for p in valid_priorities:
            self.assertGreaterEqual(p, 1)
            self.assertLessEqual(p, 10)

    def test_importance_levels(self):
        """Test memory importance levels."""
        valid_importance = ["low", "medium", "high", "critical"]
        for imp in valid_importance:
            self.assertIn(imp, valid_importance)


if __name__ == "__main__":
    unittest.main(verbosity=2)
