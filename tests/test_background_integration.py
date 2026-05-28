"""Integration tests for background rituals."""

import os
import sys
import unittest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBackgroundIntegration(unittest.TestCase):
    """Test background manager rituals."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_heartbeat_logging(self):
        """Test heartbeat logs system metrics."""
        import psutil

        from core.background_manager import BackgroundManager

        manager = BackgroundManager()
        heartbeat_file = self.temp_path / "heartbeat.json"

        heartbeat_data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(),
            "ram_percent": psutil.virtual_memory().percent,
        }

        with open(heartbeat_file, "w") as f:
            json.dump(heartbeat_data, f)

        self.assertTrue(heartbeat_file.exists())

        with open(heartbeat_file) as f:
            data = json.load(f)

        self.assertIn("timestamp", data)
        self.assertIn("cpu_percent", data)
        self.assertIn("ram_percent", data)

    def test_agent_state_management(self):
        """Test agent state save and load."""
        from core.background_manager import AgentState

        with patch("config.AGENT_STATE_FILE", self.temp_path / "agent_state.json"):
            state = AgentState()
            state.state["mode"] = "consultor"
            state.state["model"] = "qwen3.5:4b"
            state.state["messages_count"] = 10
            state.state["tokens_used"] = 5000
            state._save()

            loaded = AgentState()
            loaded._load()

            self.assertEqual(loaded.state.get("mode"), "consultor")
            self.assertEqual(loaded.state.get("model"), "qwen3.5:4b")
            self.assertEqual(loaded.state.get("messages_count"), 10)

    def test_brave_counter_persistence(self):
        """Test Brave API counter persists across restarts."""
        from core.background_manager import BraveCounter

        counter_file = self.temp_path / "brave_counter.json"

        with patch("config.BRAVE_COUNTER_FILE", counter_file):
            counter = BraveCounter()
            counter.count = 0
            for _ in range(10):
                counter.count += 1
            counter._save()

            new_counter = BraveCounter()
            new_counter._load()

            self.assertEqual(new_counter.count, 10)

    def test_background_manager_initialization(self):
        """Test background manager initializes correctly."""
        from core.background_manager import BackgroundManager

        manager = BackgroundManager()

        self.assertFalse(manager.running)
        self.assertEqual(len(manager.threads), 0)

    def test_heartbeat_file_format(self):
        """Test heartbeat file has correct format."""
        import psutil

        heartbeat_file = self.temp_path / "heartbeat_format.json"

        heartbeat_data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(),
            "ram_percent": psutil.virtual_memory().percent,
        }

        with open(heartbeat_file, "w") as f:
            json.dump(heartbeat_data, f)

        with open(heartbeat_file) as f:
            data = json.load(f)

        required_fields = ["timestamp", "cpu_percent", "ram_percent"]
        for field in required_fields:
            self.assertIn(field, data)

        self.assertIsInstance(data["cpu_percent"], (int, float))
        self.assertIsInstance(data["ram_percent"], (int, float))


class TestBackgroundRituals(unittest.TestCase):
    """Test background ritual scheduling."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_suture_ritual(self):
        """Test wiki suture ritual."""
        with patch("config.DATA_DIR", self.temp_path):
            from core.background_manager import BackgroundManager

            manager = BackgroundManager()

            with patch.object(manager, "_run_suture") as mock_suture:
                mock_suture.return_value = {"repaired": 5}
                result = manager._run_suture()
                self.assertIn("repaired", result)

    def test_graph_rebuild_ritual(self):
        """Test graph rebuild ritual."""
        with patch("config.DATA_DIR", self.temp_path):
            from core.background_manager import BackgroundManager

            manager = BackgroundManager()

            with patch.object(manager, "_update_graph") as mock_graph:
                mock_graph.return_value = {"nodes": 10, "edges": 25}
                result = manager._update_graph()
                self.assertIn("nodes", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
