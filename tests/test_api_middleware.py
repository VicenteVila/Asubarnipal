"""Tests for api/middleware.py."""

import time
import unittest
from unittest.mock import Mock, patch, AsyncMock
from collections import defaultdict


class TestMetricsMiddleware(unittest.TestCase):
    """Test metrics collection middleware."""

    def test_metrics_initialization(self):
        from api.middleware import MetricsMiddleware

        mock_app = Mock()
        middleware = MetricsMiddleware(mock_app)

        self.assertEqual(middleware._metrics["total_requests"], 0)
        self.assertEqual(middleware._metrics["total_errors"], 0)

    def test_get_metrics_returns_expected_fields(self):
        from api.middleware import MetricsMiddleware

        mock_app = Mock()
        middleware = MetricsMiddleware(mock_app)

        metrics = middleware.get_metrics()

        self.assertIn("total_requests", metrics)
        self.assertIn("total_errors", metrics)
        self.assertIn("error_rate", metrics)
        self.assertIn("requests_by_endpoint", metrics)
        self.assertIn("avg_response_time", metrics)
        self.assertIn("timestamp", metrics)

    def test_error_rate_calculation(self):
        from api.middleware import MetricsMiddleware

        mock_app = Mock()
        middleware = MetricsMiddleware(mock_app)

        middleware._metrics["total_requests"] = 100
        middleware._metrics["total_errors"] = 10

        metrics = middleware.get_metrics()
        self.assertAlmostEqual(metrics["error_rate"], 0.1, places=2)


class TestRateLimitMiddleware(unittest.TestCase):
    """Test rate limiting middleware."""

    def test_rate_limiter_allows_within_limit(self):
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=10, refill_rate=10, refill_interval=60)

        for i in range(10):
            self.assertTrue(limiter.allow("test_ip"))

        self.assertFalse(limiter.allow("test_ip"))

    def test_rate_limiter_tracks_per_key(self):
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=2, refill_rate=2, refill_interval=60)

        limiter.allow("ip1")
        limiter.allow("ip1")
        self.assertFalse(limiter.allow("ip1"))

        self.assertTrue(limiter.allow("ip2"))


if __name__ == "__main__":
    unittest.main()
