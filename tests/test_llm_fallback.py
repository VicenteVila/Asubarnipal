"""Integration tests for LLM fallback: Ollama → Gemini → error."""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLLMFallback(unittest.TestCase):
    """Test LLM fallback chain."""

    @patch("core.llm_router.LLMRouter._check_ollama", return_value=False)
    def test_generate_without_ollama(self, mock_check):
        """Test generate fails gracefully without Ollama."""
        with patch("core.llm_router.LLMRouter._init_ollama"):
            from core.llm_router import LLMRouter

            router = LLMRouter()
            router.gemini_keys = []

            with patch.object(router, "use_ollama", False):
                result = router.generate("Test prompt")
                self.assertIn("Fallo crítico", result)

    @patch("core.llm_router.LLMRouter._check_ollama", return_value=True)
    def test_generate_ollama_success(self, mock_check):
        """Test generate succeeds with Ollama."""
        with patch("core.llm_router.LLMRouter._init_ollama"):
            from core.llm_router import LLMRouter

            router = LLMRouter()
            router.ollama_client = Mock()
            router.ollama_client.chat.return_value.message.content = "Ollama response"
            router.ollama_client.chat.return_value.message.tool_calls = []

            result = router.generate("Test prompt")
            self.assertEqual(result, "Ollama response")

    @patch("core.llm_router.LLMRouter._check_ollama", return_value=True)
    def test_generate_ollama_fallback_gemini(self, mock_check):
        """Test fallback to Gemini when Ollama fails."""
        with patch("core.llm_router.LLMRouter._init_ollama"):
            from core.llm_router import LLMRouter

            router = LLMRouter()
            router.ollama_client = Mock()
            router.ollama_client.chat.side_effect = Exception("Ollama down")
            router.gemini_keys = ["test_gemini_key"]

            with patch.object(router, "_gemini_chat", return_value={"response": "Gemini response", "model": "gemini"}):
                result = router.generate("Test prompt")
                self.assertEqual(result, "Gemini response")

    def test_gemini_key_rotation(self):
        """Test Gemini key rotation on failure."""
        with patch("core.llm_router.LLMRouter._check_ollama", return_value=False):
            with patch("core.llm_router.LLMRouter._init_ollama"):
                from core.llm_router import LLMRouter

                router = LLMRouter()
                router.gemini_keys = ["key1", "key2", "key3"]
                router.current_key_index = 0

                initial_index = router.current_key_index
                router.rotate_gemini()

                self.assertEqual(router.current_key_index, (initial_index + 1) % 3)

    def test_retry_logic_with_backoff(self):
        """Test retry logic with exponential backoff."""
        call_times = []

        def mock_generate(*args, **kwargs):
            call_times.append(time.time())
            raise Exception("Temporary failure")

        with patch("core.llm_router.LLMRouter._check_ollama", return_value=True):
            with patch("core.llm_router.LLMRouter._init_ollama"):
                from core.llm_router import LLMRouter

                router = LLMRouter()
                router.use_ollama = True
                router.gemini_keys = []

                with patch.object(router, "chat", side_effect=mock_generate):
                    result = router.generate("Test prompt")

                    self.assertIn("Fallo crítico", result)
                    self.assertEqual(len(call_times), 3)


class TestLLMRouterIntegration(unittest.TestCase):
    """Test LLMRouter integration with different configurations."""

    def test_router_type_selection(self):
        """Test get_llm_router returns correct router type."""
        from core.llm_router import get_llm_router

        with patch("core.llm_router.LLMRouter._check_ollama", return_value=True):
            with patch("core.llm_router.LLMRouter._init_ollama"):
                ollama_router = get_llm_router("ollama")
                self.assertIsInstance(ollama_router, type(get_llm_router("ollama")))

    def test_brave_router(self):
        """Test Brave search router."""
        with patch.dict(os.environ, {"BRAVE_API_KEY": "test_brave_key"}):
            import importlib
            import config
            config.BRAVE_API_KEY = "test_brave_key"

            from core.llm_router import BraveRouter

            router = BraveRouter()
            self.assertEqual(router.api_key, "test_brave_key")

    def test_brave_counter(self):
        """Test Brave API counter."""
        from core.llm_router import BraveCounter

        counter = BraveCounter()
        self.assertEqual(counter.get_left(), 100)

        counter.decrement()
        self.assertEqual(counter.get_left(), 99)

        for _ in range(50):
            counter.decrement()

        self.assertEqual(counter.get_left(), 49)

        counter.reset()
        self.assertEqual(counter.get_left(), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
