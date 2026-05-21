"""Rate limiter for API and Telegram commands."""

import time
from collections import defaultdict
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        max_tokens: int = 10,
        refill_rate: float = 1.0,
        refill_interval: float = 60.0,
    ) -> None:
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self._buckets: dict[str, dict] = {}

    def _get_bucket(self, key: str) -> dict:
        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": self.max_tokens,
                "last_refill": time.time(),
            }
        return self._buckets[key]

    def _refill(self, bucket: dict) -> None:
        now = time.time()
        elapsed = now - bucket["last_refill"]
        tokens_to_add = (elapsed / self.refill_interval) * self.refill_rate
        bucket["tokens"] = min(self.max_tokens, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now

    def allow(self, key: str, tokens: int = 1) -> bool:
        bucket = self._get_bucket(key)
        self._refill(bucket)
        if bucket["tokens"] >= tokens:
            bucket["tokens"] -= tokens
            return True
        return False

    def remaining(self, key: str) -> int:
        bucket = self._get_bucket(key)
        self._refill(bucket)
        return int(bucket["tokens"])

    def reset(self, key: str) -> None:
        if key in self._buckets:
            del self._buckets[key]


class CommandRateLimiter:
    """Rate limiter for Telegram commands."""

    def __init__(self) -> None:
        self._limiters = {
            "default": RateLimiter(max_tokens=30, refill_rate=30, refill_interval=60),
            "investigar": RateLimiter(max_tokens=5, refill_rate=5, refill_interval=300),
            "agente": RateLimiter(max_tokens=10, refill_rate=10, refill_interval=60),
            "ingest": RateLimiter(max_tokens=10, refill_rate=10, refill_interval=60),
            "schedule": RateLimiter(max_tokens=5, refill_rate=5, refill_interval=300),
        }

    def allow(self, user_id: int, command: str) -> tuple[bool, int]:
        limiter = self._limiters.get(command, self._limiters["default"])
        key = f"{user_id}:{command}"
        allowed = limiter.allow(key)
        remaining = limiter.remaining(key)
        return allowed, remaining

    def get_wait_time(self, user_id: int, command: str) -> float:
        limiter = self._limiters.get(command, self._limiters["default"])
        key = f"{user_id}:{command}"
        bucket = limiter._get_bucket(key)
        if bucket["tokens"] < 1:
            deficit = 1 - bucket["tokens"]
            return (deficit / limiter.refill_rate) * limiter.refill_interval
        return 0.0


_command_limiter: Optional[CommandRateLimiter] = None


def get_command_limiter() -> CommandRateLimiter:
    global _command_limiter
    if _command_limiter is None:
        _command_limiter = CommandRateLimiter()
    return _command_limiter
