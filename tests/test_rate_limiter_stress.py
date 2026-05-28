"""Stress tests for rate limiter under heavy load."""

import os
import sys
import unittest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRateLimiterStress(unittest.TestCase):
    """Test rate limiter under heavy concurrent load."""

    def test_high_concurrency_single_user(self):
        """Test rate limiter with many concurrent requests from single user."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=100, refill_rate=100, refill_interval=60)

        results = []

        def make_request():
            return limiter.allow("stress_user")

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(200)]

            for future in as_completed(futures):
                results.append(future.result())

        allowed = sum(1 for r in results if r)
        denied = sum(1 for r in results if not r)

        self.assertEqual(allowed, 100)
        self.assertEqual(denied, 100)
        self.assertEqual(len(results), 200)

    def test_high_concurrency_multiple_users(self):
        """Test rate limiter with many concurrent users."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=5, refill_rate=5, refill_interval=60)

        results = []

        def make_request(user_id):
            return limiter.allow(f"user_{user_id}")

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = []
            for i in range(100):
                user_id = i % 20
                futures.append(executor.submit(make_request, user_id))

            for future in as_completed(futures):
                results.append(future.result())

        allowed = sum(1 for r in results if r)
        self.assertGreater(allowed, 0)
        self.assertEqual(len(results), 100)

    def test_refill_after_interval(self):
        """Test tokens refill after interval."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=5, refill_rate=5, refill_interval=0.1)

        for _ in range(5):
            self.assertTrue(limiter.allow("refill_user"))

        self.assertFalse(limiter.allow("refill_user"))

        time.sleep(0.15)

        self.assertTrue(limiter.allow("refill_user"))

    def test_command_rate_limiter(self):
        """Test command-specific rate limiting."""
        from core.rate_limiter import CommandRateLimiter

        limiter = CommandRateLimiter()

        allowed, remaining = limiter.allow(123, "investigar")
        self.assertTrue(allowed)

        for _ in range(4):
            limiter.allow(123, "investigar")

        allowed, remaining = limiter.allow(123, "investigar")
        self.assertFalse(allowed)

        default_allowed, _ = limiter.allow(123, "unknown_command")
        self.assertTrue(default_allowed)

    def test_wait_time_calculation(self):
        """Test wait time calculation when rate limited."""
        from core.rate_limiter import CommandRateLimiter

        limiter = CommandRateLimiter()

        for _ in range(5):
            limiter.allow(456, "investigar")

        wait_time = limiter.get_wait_time(456, "investigar")
        self.assertGreater(wait_time, 0)

    def test_rate_limiter_reset(self):
        """Test rate limiter reset functionality."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=2, refill_rate=2, refill_interval=60)

        limiter.allow("reset_user")
        limiter.allow("reset_user")
        self.assertFalse(limiter.allow("reset_user"))

        limiter.reset("reset_user")
        self.assertTrue(limiter.allow("reset_user"))


class TestRateLimiterEdgeCases(unittest.TestCase):
    """Test edge cases for rate limiter."""

    def test_zero_max_tokens(self):
        """Test rate limiter with zero max tokens."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=0, refill_rate=1, refill_interval=60)
        self.assertFalse(limiter.allow("zero_user"))

    def test_very_high_rate(self):
        """Test rate limiter with very high rate."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=10000, refill_rate=10000, refill_interval=1)

        for _ in range(1000):
            self.assertTrue(limiter.allow("high_rate_user"))

    def test_negative_tokens_request(self):
        """Test requesting negative tokens."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=10, refill_rate=10, refill_interval=60)
        self.assertTrue(limiter.allow("negative_user", tokens=-1))

    def test_large_token_request(self):
        """Test requesting more tokens than available."""
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=10, refill_rate=10, refill_interval=60)
        self.assertFalse(limiter.allow("large_user", tokens=20))


if __name__ == "__main__":
    unittest.main(verbosity=2)
