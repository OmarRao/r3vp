# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Fixed-window rate limiting middleware.

Limits requests per client identity (API key if present, else client IP) within
a rolling fixed window, emits standard ``X-RateLimit-*`` headers on every
response, and returns 429 with ``Retry-After`` when the limit is exceeded. The
counter store is in-process; the same interface can be backed by a shared store
(Redis) for multi-instance deployments.
"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Paths that must never be rate limited (health probes, docs, metrics).
_EXCLUDED_PREFIXES = ("/health", "/ready", "/live", "/metrics", "/docs", "/redoc", "/openapi.json")

# Bound the in-process store so a flood of unique clients cannot grow it without
# limit; stale windows are purged when the store exceeds this many keys.
_MAX_TRACKED_KEYS = 10_000


class FixedWindowRateLimiter:
    """Counts requests per key within aligned fixed windows of ``window_seconds``."""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, tuple[int, int]] = {}

    def hit(self, key: str, now: float | None = None) -> tuple[bool, int, int, int]:
        """Register one request for ``key``.

        Returns ``(allowed, limit, remaining, reset_epoch)``.
        """
        now = time.time() if now is None else now
        window_start = int(now // self.window) * self.window
        count, start = self._hits.get(key, (0, window_start))
        if start != window_start:
            count, start = 0, window_start
        count += 1
        self._hits[key] = (count, start)
        if len(self._hits) > _MAX_TRACKED_KEYS:
            self._purge(window_start)
        remaining = max(0, self.limit - count)
        reset = start + self.window
        return count <= self.limit, self.limit, remaining, reset

    def _purge(self, current_window_start: int) -> None:
        self._hits = {
            k: v for k, v in self._hits.items() if v[1] >= current_window_start
        }


def client_key(request: Request) -> str:
    """Identify the caller: API key if supplied, otherwise the client IP."""
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"key:{api_key[:16]}"
    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: FixedWindowRateLimiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if any(request.url.path.startswith(p) for p in _EXCLUDED_PREFIXES):
            return await call_next(request)

        allowed, limit, remaining, reset = self.limiter.hit(client_key(request))
        if not allowed:
            retry_after = max(1, reset - int(time.time()))
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry later."},
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                    "Retry-After": str(retry_after),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        return response
