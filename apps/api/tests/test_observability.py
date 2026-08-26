# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Tests for the liveness probe and Prometheus metrics endpoint (no DB needed)."""
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_live_probe():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/live")            # generate one request to record
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "# HELP" in body and "# TYPE" in body   # Prometheus exposition format
    assert "http_request" in body                  # request metrics are recorded
