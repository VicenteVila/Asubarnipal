"""Tests for api/auth.py."""

import asyncio
import os
import unittest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException


class TestAPIAuth(unittest.TestCase):
    """Test API key authentication."""

    def setUp(self):
        import importlib
        import api.auth
        api.auth._API_KEYS = None
        importlib.reload(api.auth)

    def tearDown(self):
        import api.auth
        api.auth._API_KEYS = None

    def _run_async(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_get_api_keys_from_env(self):
        with patch.dict(os.environ, {"API_KEYS": "key1,key2,key3"}):
            from api.auth import get_api_keys

            keys = get_api_keys()
            self.assertEqual(keys, {"key1", "key2", "key3"})

    def test_get_api_keys_empty_env(self):
        with patch.dict(os.environ, {"API_KEYS": ""}, clear=False):
            from api.auth import get_api_keys

            keys = get_api_keys()
            self.assertEqual(keys, set())

    def test_verify_api_key_no_keys_configured(self):
        with patch.dict(os.environ, {"API_KEYS": ""}, clear=False):
            from api.auth import verify_api_key

            mock_request = MagicMock()
            self._run_async(verify_api_key(mock_request))

    def test_verify_api_key_valid(self):
        with patch.dict(os.environ, {"API_KEYS": "secret123"}):
            from api.auth import verify_api_key

            mock_request = MagicMock()
            self._run_async(verify_api_key(mock_request, api_key="secret123"))

    def test_verify_api_key_invalid(self):
        with patch.dict(os.environ, {"API_KEYS": "secret123"}):
            from api.auth import verify_api_key

            mock_request = MagicMock()

            with self.assertRaises(HTTPException):
                self._run_async(verify_api_key(mock_request, api_key="wrong_key"))

    def test_verify_api_key_missing(self):
        with patch.dict(os.environ, {"API_KEYS": "secret123"}):
            from api.auth import verify_api_key

            mock_request = MagicMock()

            with self.assertRaises(HTTPException):
                self._run_async(verify_api_key(mock_request))

    def test_verify_api_key_from_header(self):
        with patch.dict(os.environ, {"API_KEYS": "secret123"}):
            from api.auth import verify_api_key

            mock_request = MagicMock()
            mock_request.headers = {"X-API-Key": "secret123"}

            self._run_async(verify_api_key(mock_request))


if __name__ == "__main__":
    unittest.main()
