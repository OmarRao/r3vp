# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Tests for security response headers and the request-id middleware."""
import pytest
from httpx import ASGITransport, AsyncClient

from src.http_hardening import SECURITY_HEADERS
from src.main import app


@pytest.mark.asyncio
async def test_security_headers_present():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/live")
    for header, value in SECURITY_HEADERS.items():
        assert resp.headers.get(header.lower()) == value
    assert resp.headers.get("x-request-id")   # correlation id assigned


@pytest.mark.asyncio
async def test_inbound_request_id_is_echoed():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/live", headers={"x-request-id": "trace-abc-123"})
    assert resp.headers.get("x-request-id") == "trace-abc-123"
