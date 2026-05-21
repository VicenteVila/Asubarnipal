"""Middleware for FastAPI - rate limiting, auth, metrics."""

import time
from collections import defaultdict
from datetime import datetime
from typing import Callable

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse

import config
from core.bot_logger import logger


class RateLimitMiddleware:
    """Rate limiting middleware for API endpoints."""

    def __init__(
        self,
        app: FastAPI,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> None:
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, key: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        self._cleanup(client_ip, now)

        if len(self._requests[client_ip]) >= self.max_requests:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": self.window_seconds,
                },
            )
            await response(scope, receive, send)
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return

        self._requests[client_ip].append(now)

        await self.app(scope, receive, send)


class MetricsMiddleware:
    """Collect request metrics for monitoring."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self._metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "requests_by_endpoint": defaultdict(int),
            "errors_by_endpoint": defaultdict(int),
            "response_times": [],
        }

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path
        start_time = time.time()

        self._metrics["total_requests"] += 1
        self._metrics["requests_by_endpoint"][path] += 1

        try:
            await self.app(scope, receive, send)
        except Exception as e:
            self._metrics["total_errors"] += 1
            self._metrics["errors_by_endpoint"][path] += 1
            logger.error(f"API error on {path}: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self._metrics["response_times"].append(duration)
            if len(self._metrics["response_times"]) > 1000:
                self._metrics["response_times"] = self._metrics["response_times"][-1000:]

    def get_metrics(self) -> dict:
        times = self._metrics["response_times"]
        return {
            "total_requests": self._metrics["total_requests"],
            "total_errors": self._metrics["total_errors"],
            "error_rate": (
                self._metrics["total_errors"] / max(1, self._metrics["total_requests"])
            ),
            "requests_by_endpoint": dict(self._metrics["requests_by_endpoint"]),
            "errors_by_endpoint": dict(self._metrics["errors_by_endpoint"]),
            "avg_response_time": sum(times) / max(1, len(times)),
            "p95_response_time": sorted(times)[int(len(times) * 0.95)] if times else 0,
            "timestamp": datetime.now().isoformat(),
        }


_metrics: MetricsMiddleware | None = None


def get_metrics_middleware() -> MetricsMiddleware:
    global _metrics
    if _metrics is None:
        raise RuntimeError("MetricsMiddleware not initialized")
    return _metrics


def init_metrics(app: FastAPI) -> MetricsMiddleware:
    global _metrics
    _metrics = MetricsMiddleware(app)
    return _metrics
