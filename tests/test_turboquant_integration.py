"""Integration tests for TurboQuant engine."""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTurboQuantIntegration(unittest.TestCase):
    """Test TurboQuant engine end-to-end."""

    def setUp(self):
        from core.turboquant_engine import TurboQuantEngine
        TurboQuantEngine._instance = None
        TurboQuantEngine._initialized = False

    def tearDown(self):
        from core.turboquant_engine import TurboQuantEngine
        TurboQuantEngine._instance = None
        TurboQuantEngine._initialized = False

    @patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=False)
    def test_engine_initialization_no_ollama(self, mock_check):
        """Test engine initializes without Ollama."""
        from core.turboquant_engine import TurboQuantEngine

        engine = TurboQuantEngine()

        self.assertFalse(engine._ollama_available)
        self.assertEqual(engine._gguf_models, [])

    @patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=True)
    @patch("core.turboquant_engine.TurboQuantEngine._detect_gguf_models", return_value=["qwen3.5:4b"])
    def test_engine_initialization_with_ollama(self, mock_detect, mock_check):
        """Test engine initializes with Ollama."""
        from core.turboquant_engine import TurboQuantEngine

        engine = TurboQuantEngine()

        self.assertTrue(engine._ollama_available)
        self.assertIn("qwen3.5:4b", engine._gguf_models)

    @patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=True)
    @patch("core.turboquant_engine.TurboQuantEngine._detect_gguf_models", return_value=["qwen3.5:4b"])
    def test_apply_mode_consultor(self, mock_detect, mock_check):
        """Test applying consultor mode."""
        from core.turboquant_engine import TurboQuantEngine

        engine = TurboQuantEngine()
        result = engine.apply_mode("consultor")

        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "consultor")
        self.assertIn("context", result["config_applied"])
        self.assertIn("cache_k", result["config_applied"])

    @patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=True)
    @patch("core.turboquant_engine.TurboQuantEngine._detect_gguf_models", return_value=["qwen3.5:4b"])
    def test_apply_mode_libre(self, mock_detect, mock_check):
        """Test applying libre mode (speed optimized)."""
        from core.turboquant_engine import TurboQuantEngine

        engine = TurboQuantEngine()
        result = engine.apply_mode("libre")

        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "libre")

    @patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=True)
    @patch("core.turboquant_engine.TurboQuantEngine._detect_gguf_models", return_value=["qwen3.5:4b"])
    def test_apply_mode_devil(self, mock_detect, mock_check):
        """Test applying devil mode (quality optimized)."""
        from core.turboquant_engine import TurboQuantEngine

        engine = TurboQuantEngine()
        result = engine.apply_mode("devil")

        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "devil")

    @patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=True)
    @patch("core.turboquant_engine.TurboQuantEngine._detect_gguf_models", return_value=["qwen3.5:4b"])
    def test_get_optimized_params(self, mock_detect, mock_check):
        """Test getting optimized parameters."""
        from core.turboquant_engine import TurboQuantEngine

        engine = TurboQuantEngine()
        engine.apply_mode("consultor")

        params = engine.get_optimized_params()

        self.assertIn("context", params)
        self.assertIn("options", params)
        self.assertIn("turbo", params)
        self.assertIn("num_ctx", params["options"])
        self.assertIn("cache_k", params["turbo"])

    @patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=True)
    @patch("core.turboquant_engine.TurboQuantEngine._detect_gguf_models", return_value=["qwen3.5:4b"])
    def test_state_tracking(self, mock_detect, mock_check):
        """Test engine tracks state correctly."""
        from core.turboquant_engine import TurboQuantEngine

        engine = TurboQuantEngine()

        self.assertFalse(engine.state.is_applied)

        engine.apply_mode("consultor")

        self.assertTrue(engine.state.is_applied)
        self.assertEqual(engine.state.mode, "consultor")
        self.assertIsNotNone(engine.state.last_applied)

    @patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=True)
    @patch("core.turboquant_engine.TurboQuantEngine._detect_gguf_models", return_value=["qwen3.5:4b"])
    def test_reset_state(self, mock_detect, mock_check):
        """Test resetting engine state."""
        from core.turboquant_engine import TurboQuantEngine

        engine = TurboQuantEngine()
        engine.apply_mode("consultor")
        self.assertTrue(engine.state.is_applied)

        engine.reset()
        self.assertFalse(engine.state.is_applied)
        self.assertIsNone(engine.state.mode)

    @patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=False)
    def test_benchmark_no_ollama(self, mock_check):
        """Test benchmark fails gracefully without Ollama."""
        from core.turboquant_engine import TurboQuantEngine

        engine = TurboQuantEngine()
        result = engine.benchmark()

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_singleton_pattern(self):
        """Test engine is a singleton."""
        with patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=False):
            from core.turboquant_engine import TurboQuantEngine, get_engine

            engine1 = get_engine()
            engine2 = get_engine()

            self.assertIs(engine1, engine2)

    def test_convenience_functions(self):
        """Test convenience functions work correctly."""
        with patch("core.turboquant_engine.TurboQuantEngine._check_ollama", return_value=False):
            from core.turboquant_engine import (
                get_engine,
                apply_chat_mode,
                get_turbo_params,
                get_turbo_status,
            )

            status = get_turbo_status()
            self.assertIsInstance(status, dict)

            result = apply_chat_mode("consultor")
            self.assertIn("success", result)

            params = get_turbo_params("consultor")
            self.assertIn("context", params)


if __name__ == "__main__":
    unittest.main(verbosity=2)
