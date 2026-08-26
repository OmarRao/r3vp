# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Integration test: the readiness probe reports ready when the DB is reachable."""
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_ready_probe_ok_with_db(db_engine):
    # db_engine ensures the configured database is up and reachable.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}
