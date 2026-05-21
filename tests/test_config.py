"""Unit tests for config.py."""
import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig(unittest.TestCase):
    """Test configuration module."""

    def test_config_imports(self):
        """Test config module imports successfully."""
        import config
        self.assertIsNotNone(config)

    def test_base_dir_exists(self):
        """Test BASE_DIR is set correctly."""
        import config
        self.assertTrue(config.BASE_DIR.exists())

    def test_data_dir_defined(self):
        """Test DATA_DIR is defined."""
        import config
        self.assertIsNotNone(config.DATA_DIR)

    def test_telegram_token_env(self):
        """Test TELEGRAM_TOKEN reads from environment."""
        with patch.dict(os.environ, {"TELEGRAM_TOKEN": "test_token_123"}):
            # Re-import to get patched value
            import importlib
            import config
            importlib.reload(config)
            self.assertEqual(config.TELEGRAM_TOKEN, "test_token_123")

    def test_ollama_base_url_default(self):
        """Test OLLAMA_BASE_URL has default value."""
        import config
        self.assertEqual(config.OLLAMA_BASE_URL, "http://127.0.0.1:11434")

    def test_ollama_model_default(self):
        """Test OLLAMA_MODEL has default value."""
        import config
        self.assertEqual(config.OLLAMA_MODEL, "qwen3.5:4b")

    def test_brave_monthly_limit(self):
        """Test BRAVE_MONTHLY_LIMIT is set."""
        import config
        self.assertEqual(config.BRAVE_MONTHLY_LIMIT, 1500)

    def test_heartbeat_interval(self):
        """Test HEARTBEAT_INTERVAL is set."""
        import config
        self.assertEqual(config.HEARTBEAT_INTERVAL, 60)

    def test_suture_interval(self):
        """Test SUTURE_INTERVAL is set."""
        import config
        self.assertEqual(config.SUTURE_INTERVAL, 600)

    def test_graph_interval(self):
        """Test GRAPH_INTERVAL is set."""
        import config
        self.assertEqual(config.GRAPH_INTERVAL, 1800)

    def test_ensure_directories(self):
        """Test ensure_directories creates directories."""
        import config
        # Should not raise
        config.ensure_directories()
        self.assertTrue(config.DATA_DIR.exists())


class TestConfigPaths(unittest.TestCase):
    """Test configuration paths."""

    def test_wiki_path_defined(self):
        """Test WIKI_PATH is defined."""
        import config
        self.assertIsNotNone(config.WIKI_PATH)

    def test_vector_index_defined(self):
        """Test VECTOR_INDEX is defined."""
        import config
        self.assertIsNotNone(config.VECTOR_INDEX)

    def test_heartbeat_file_defined(self):
        """Test HEARTBEAT_FILE is defined."""
        import config
        self.assertIsNotNone(config.HEARTBEAT_FILE)

    def test_log_file_defined(self):
        """Test LOG_FILE is defined."""
        import config
        self.assertIsNotNone(config.LOG_FILE)

    def test_manual_file_defined(self):
        """Test MANUAL_FILE is defined."""
        import config
        self.assertIsNotNone(config.MANUAL_FILE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
