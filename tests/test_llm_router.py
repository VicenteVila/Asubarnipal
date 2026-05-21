"""Unit tests for llm_router.py."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests


class MockResponse:
    def __init__(self, json_data=None, status_code=200):
        self.json_data = json_data or {}
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError()


class TestLLMRouter(unittest.TestCase):
    """Test LLMRouter class."""

    def setUp(self):
        self.patcher = patch('requests.get')
        self.mock_get = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_check_ollama_available(self):
        self.mock_get.return_value.status_code = 200
        from core.llm_router import LLMRouter
        router = LLMRouter()
        self.assertTrue(router.use_ollama)

    def test_check_ollama_unavailable(self):
        self.mock_get.side_effect = requests.exceptions.ConnectionError()
        from core.llm_router import LLMRouter
        router = LLMRouter()
        self.assertFalse(router.use_ollama)

    def test_prepare_messages_converts_correctly(self):
        self.mock_get.side_effect = requests.exceptions.ConnectionError()
        from core.llm_router import LLMRouter
        router = LLMRouter()
        messages = [{"role": "user", "content": "test"}]
        result = router._prepare_messages(messages)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "user")

    def test_prepare_messages_with_object(self):
        self.mock_get.side_effect = requests.exceptions.ConnectionError()
        from core.llm_router import LLMRouter
        router = LLMRouter()
        mock_msg = Mock()
        mock_msg.role = "assistant"
        mock_msg.content = "response"
        result = router._prepare_messages([mock_msg])
        self.assertEqual(result[0]["role"], "assistant")


class TestGeminiRouter(unittest.TestCase):
    """Test GeminiRouter class."""

    @patch('requests.post')
    def test_gemini_chat_success(self, mock_post):
        mock_post.return_value = MockResponse(json_data={
            "candidates": [{
                "content": {
                    "parts": [{"text": "test response"}]
                }
            }]
        })
        mock_post.return_value.raise_for_status = Mock()
        from core.llm_router import GeminiRouter
        router = GeminiRouter()
        result = router.chat([{"role": "user", "content": "test"}])
        self.assertEqual(result["response"], "test response")

    def test_gemini_no_keys_raises(self):
        with patch('config.GEMINI_KEYS', []):
            from core.llm_router import GeminiRouter
            router = GeminiRouter()
            with self.assertRaises(ValueError):
                router.chat([{"role": "user", "content": "test"}])


class TestBraveRouter(unittest.TestCase):
    """Test BraveRouter class."""

    @patch('requests.get')
    def test_brave_search_returns_results(self, mock_get):
        mock_get.return_value = MockResponse(json_data={
            "web": {
                "results": [
                    {"title": "Test", "url": "http://test.com", "description": "desc"}
                ]
            }
        })
        mock_get.return_value.raise_for_status = Mock()
        with patch('config.BRAVE_API_KEY', 'fake_key'):
            from core.llm_router import BraveRouter
            router = BraveRouter()
            results = router.search("test query")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Test")

    def test_brave_no_api_key_raises(self):
        with patch('config.BRAVE_API_KEY', ''):
            from core.llm_router import BraveRouter
            with self.assertRaises(ValueError):
                BraveRouter()


class TestBraveCounter(unittest.TestCase):
    """Test BraveCounter class."""

    def test_get_left(self):
        from core.llm_router import BraveCounter
        counter = BraveCounter()
        counter.count = 30
        self.assertEqual(counter.get_left(), 70)

    def test_decrement(self):
        from core.llm_router import BraveCounter
        counter = BraveCounter()
        counter.decrement()
        self.assertEqual(counter.count, 1)

    def test_reset(self):
        from core.llm_router import BraveCounter
        counter = BraveCounter()
        counter.count = 50
        counter.reset()
        self.assertEqual(counter.count, 0)


class TestGetLLMRouter(unittest.TestCase):
    """Test get_llm_router factory."""

    def test_get_ollama_router(self):
        from core.llm_router import get_llm_router
        router = get_llm_router("ollama")
        self.assertIsNotNone(router)

    def test_get_gemini_router(self):
        from core.llm_router import get_llm_router
        router = get_llm_router("gemini")
        self.assertIsNotNone(router)


if __name__ == '__main__':
    unittest.main(verbosity=2)