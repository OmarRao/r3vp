# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Tests for the fixed-window rate limiter and its middleware."""
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.rate_limit import FixedWindowRateLimiter, RateLimitMiddleware


def test_limiter_allows_up_to_limit_then_blocks():
    rl = FixedWindowRateLimiter(limit=3, window_seconds=60)
    results = [rl.hit("k", now=1000.0) for _ in range(4)]
    assert [r[0] for r in results] == [True, True, True, False]   # allowed flags
    assert [r[2] for r in results] == [2, 1, 0, 0]                # remaining
    assert results[0][3] == 1020                                  # reset = 960 + 60


def test_limiter_resets_in_next_window():
    rl = FixedWindowRateLimiter(limit=1, window_seconds=60)
    assert rl.hit("k", now=1000.0)[0] is True    # window starting 960
    assert rl.hit("k", now=1010.0)[0] is False   # same window -> blocked
    assert rl.hit("k", now=1080.0)[0] is True     # new window -> allowed again


def test_limiter_tracks_keys_independently():
    rl = FixedWindowRateLimiter(limit=1, window_seconds=60)
    assert rl.hit("a", now=1000.0)[0] is True
    assert rl.hit("b", now=1000.0)[0] is True     # separate budget
    assert rl.hit("a", now=1000.0)[0] is False    # "a" already spent


def _app(limit: int, path: str = "/ping") -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limiter=FixedWindowRateLimiter(limit, window_seconds=60))

    @app.get(path)
    async def _endpoint() -> dict:
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_middleware_headers_and_429():
    transport = ASGITransport(app=_app(limit=2))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/ping")
        r2 = await client.get("/ping")
        r3 = await client.get("/ping")

    assert r1.status_code == 200
    assert r1.headers["x-ratelimit-limit"] == "2"
    assert r1.headers["x-ratelimit-remaining"] == "1"
    assert r2.headers["x-ratelimit-remaining"] == "0"
    assert r3.status_code == 429
    assert r3.headers["x-ratelimit-remaining"] == "0"
    assert "retry-after" in r3.headers


@pytest.mark.asyncio
async def test_middleware_skips_excluded_paths():
    transport = ASGITransport(app=_app(limit=1, path="/health"))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        last = None
        for _ in range(3):
            last = await client.get("/health")
            assert last.status_code == 200          # health is never limited
    assert "x-ratelimit-limit" not in last.headers
