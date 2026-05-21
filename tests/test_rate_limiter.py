"""Tests for core/rate_limiter.py."""

import time
import unittest


class TestRateLimiter(unittest.TestCase):
    """Test token bucket rate limiter."""

    def test_allow_within_limit(self):
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=5, refill_rate=5, refill_interval=60)

        for i in range(5):
            self.assertTrue(limiter.allow("user1"))

        self.assertFalse(limiter.allow("user1"))

    def test_remaining_tokens(self):
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=10, refill_rate=10, refill_interval=60)

        self.assertEqual(limiter.remaining("user1"), 10)
        limiter.allow("user1")
        self.assertEqual(limiter.remaining("user1"), 9)

    def test_reset_bucket(self):
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=3, refill_rate=3, refill_interval=60)

        for _ in range(3):
            limiter.allow("user1")

        self.assertFalse(limiter.allow("user1"))
        limiter.reset("user1")
        self.assertTrue(limiter.allow("user1"))

    def test_multiple_users_independent(self):
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=1, refill_rate=1, refill_interval=60)

        self.assertTrue(limiter.allow("user1"))
        self.assertFalse(limiter.allow("user1"))
        self.assertTrue(limiter.allow("user2"))

    def test_refill_over_time(self):
        from core.rate_limiter import RateLimiter

        limiter = RateLimiter(max_tokens=2, refill_rate=2, refill_interval=1)

        limiter.allow("user1")
        limiter.allow("user1")
        self.assertFalse(limiter.allow("user1"))

        time.sleep(1.1)

        self.assertTrue(limiter.allow("user1"))


class TestCommandRateLimiter(unittest.TestCase):
    """Test command-specific rate limiter."""

    def test_default_command_limit(self):
        from core.rate_limiter import CommandRateLimiter

        limiter = CommandRateLimiter()

        for _ in range(30):
            allowed, _ = limiter.allow(1, "unknown")
            self.assertTrue(allowed)

        allowed, _ = limiter.allow(1, "unknown")
        self.assertFalse(allowed)

    def test_investigar_stricter_limit(self):
        from core.rate_limiter import CommandRateLimiter

        limiter = CommandRateLimiter()

        for _ in range(5):
            allowed, _ = limiter.allow(1, "investigar")
            self.assertTrue(allowed)

        allowed, _ = limiter.allow(1, "investigar")
        self.assertFalse(allowed)

    def test_remaining_count(self):
        from core.rate_limiter import CommandRateLimiter

        limiter = CommandRateLimiter()

        allowed, remaining = limiter.allow(1, "default")
        self.assertTrue(allowed)
        self.assertGreater(remaining, 0)

    def test_wait_time_when_exhausted(self):
        from core.rate_limiter import CommandRateLimiter

        limiter = CommandRateLimiter()

        for _ in range(30):
            limiter.allow(1, "default")

        wait = limiter.get_wait_time(1, "default")
        self.assertGreater(wait, 0)

    def test_get_command_limiter_singleton(self):
        from core.rate_limiter import get_command_limiter

        limiter1 = get_command_limiter()
        limiter2 = get_command_limiter()

        self.assertIs(limiter1, limiter2)


if __name__ == "__main__":
    unittest.main()
