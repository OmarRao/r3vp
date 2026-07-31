# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Integration test: /v1/multicloud/provider-summary over real Postgres.

Also guards against regression of the `Depends(AuthUser)` 422 auth-declaration
bug that previously broke every multicloud endpoint.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.auth import CurrentUser, get_current_user
from src.db.session import get_db
from src.main import app
from src.models.appliance import Appliance, Org
from src.models.workload import Workload

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_provider_summary_returns_breakdown(db_engine, db_session):
    org_id = uuid.uuid4()
    appliance_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="MC Org"))
    db_session.add(Appliance(id=appliance_id, org_id=org_id, name="ap-1",
                             mtls_thumbprint="t", status="active"))
    await db_session.commit()
    db_session.add(Workload(appliance_id=appliance_id, name="vm1", platform="vmware",
                            provider="vmware", rto_target_mins=30, rpo_target_mins=60))
    await db_session.commit()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="auth0|t", org_id=org_id, email="t@example.com", role="admin"
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/multicloud/provider-summary")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    # Must not 422 (the previous auth-declaration bug) and must return all providers.
    assert resp.status_code == 200
    data = resp.json()
    providers = {row["provider"] for row in data}
    assert "vmware" in providers
    vmware = next(r for r in data if r["provider"] == "vmware")
    assert vmware["total_workloads"] == 1
