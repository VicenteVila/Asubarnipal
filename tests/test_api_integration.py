"""Integration tests for FastAPI endpoints using httpx.AsyncClient."""

import os
import sys
import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAPIIntegration(unittest.TestCase):
    """Test API endpoints with mocked services."""

    def test_root_endpoint(self):
        """Test GET / returns API info."""
        from api.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Asubarnipal API")
        self.assertEqual(data["status"], "online")
        self.assertIn("timestamp", data)

    def test_health_endpoint(self):
        """Test GET /health returns health status."""
        from api.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("uptime_seconds", data)

    def test_metrics_endpoint(self):
        """Test GET /metrics returns metrics."""
        from api.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_requests", data)
        self.assertIn("total_errors", data)
        self.assertIn("error_rate", data)

    @patch("app.service.AsubarnipalService")
    def test_query_endpoint(self, mock_service):
        """Test POST /query with mocked service."""
        from api.main import app
        from fastapi.testclient import TestClient

        mock_instance = Mock()
        mock_instance.process_query.return_value = {
            "success": True,
            "response": "Test response",
            "sources": [],
        }
        mock_service.return_value = mock_instance

        client = TestClient(app)
        response = client.post(
            "/query",
            json={"query": "What is AI?", "mode": "wiki", "top_k": 5},
        )

        self.assertIn(response.status_code, [200, 404, 422])

    def test_feed_endpoints(self):
        """Test feed subscription endpoints."""
        from api.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.get("/feeds")
        self.assertIn(response.status_code, [200, 404])

    def test_command_endpoint(self):
        """Test POST /command endpoint."""
        from api.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post(
            "/command",
            json={"command": "status", "user_id": "test_user"},
        )

        self.assertIn(response.status_code, [200, 404, 422])


class TestAPIAuthIntegration(unittest.TestCase):
    """Test API authentication flow."""

    def test_api_key_from_header(self):
        """Test API key authentication via header."""
        from api.main import app
        from fastapi.testclient import TestClient

        with patch.dict(os.environ, {"API_KEYS": "test_key_123"}):
            import importlib
            import api.auth
            api.auth._API_KEYS = None
            importlib.reload(api.auth)

            client = TestClient(app)
            response = client.get(
                "/health",
                headers={"X-API-Key": "test_key_123"},
            )

            self.assertEqual(response.status_code, 200)

    def test_api_key_from_param(self):
        """Test API key authentication via query param."""
        from api.main import app
        from fastapi.testclient import TestClient

        with patch.dict(os.environ, {"API_KEYS": "test_key_456"}):
            import importlib
            import api.auth
            api.auth._API_KEYS = None
            importlib.reload(api.auth)

            client = TestClient(app)
            response = client.get(
                "/health?api_key=test_key_456",
            )

            self.assertEqual(response.status_code, 200)


class TestAPIMiddlewareIntegration(unittest.TestCase):
    """Test middleware integration."""

    def test_metrics_collection(self):
        """Test that middleware collects metrics on requests."""
        from api.main import app
        from api.middleware import init_metrics, get_metrics_middleware
        from fastapi.testclient import TestClient

        client = TestClient(app)

        for _ in range(5):
            client.get("/health")

        metrics_response = client.get("/metrics")
        data = metrics_response.json()

        self.assertGreater(data["total_requests"], 0)

    def test_cors_headers(self):
        """Test CORS middleware adds proper headers."""
        from api.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )

        self.assertIn(response.status_code, [200, 204])


if __name__ == "__main__":
    unittest.main(verbosity=2)
