# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Tenant-isolation regression tests for the appliance ingest endpoints.

These prove that an authenticated appliance cannot mutate another tenant's test
run (IDOR) and that threat-scan ingest is bound to the verified appliance
identity rather than a request-body field. Dependencies are overridden so no
Postgres is required.
"""
import types
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.db.session import get_db
from src.main import app
from src.routers.appliances import _verified_appliance


def _fake_appliance(appliance_id: uuid.UUID, org_id: uuid.UUID):
    return types.SimpleNamespace(id=appliance_id, org_id=org_id, mtls_thumbprint="AABB")


async def _dummy_db():
    yield AsyncMock()


@pytest.fixture
def client_with_appliance():
    appliance_id = uuid.uuid4()
    org_id = uuid.uuid4()
    app.dependency_overrides[_verified_appliance] = lambda: _fake_appliance(appliance_id, org_id)
    app.dependency_overrides[get_db] = _dummy_db
    try:
        yield appliance_id, org_id
    finally:
        app.dependency_overrides.pop(_verified_appliance, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_result_for_foreign_run_returns_404(client_with_appliance):
    """finalise_run raising PermissionError (run not owned) surfaces as 404."""
    with patch("src.routers.appliances.svc.finalise_run", new_callable=AsyncMock) as mock_final:
        mock_final.side_effect = PermissionError("not yours")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/v1/appliance/test-runs/{uuid.uuid4()}/result",
                json={"passed": True, "rto_actual_mins": 5, "rpo_actual_mins": 5, "readiness_score": 100},
            )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_progress_for_foreign_run_returns_404(client_with_appliance):
    with patch("src.routers.appliances.svc.update_run_progress", new_callable=AsyncMock) as mock_prog:
        mock_prog.side_effect = PermissionError("not yours")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/v1/appliance/test-runs/{uuid.uuid4()}/progress",
                json={"step": "boot", "status": "running", "detail": {}},
            )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_scan_body_appliance_id_must_match_verified(client_with_appliance):
    """A scan whose body appliance_id differs from the authenticated appliance is refused."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/v1/threat-intel/scans",
            json={
                "scan_id": "s1",
                "appliance_id": str(uuid.uuid4()),  # not the verified appliance
                "started_at": "2026-01-01T00:00:00Z",
                "completed_at": "2026-01-01T00:01:00Z",
                "findings": [],
            },
        )
    assert resp.status_code == 403
