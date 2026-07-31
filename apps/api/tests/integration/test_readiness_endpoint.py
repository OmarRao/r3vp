# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Integration test: the /v1/dashboard/readiness endpoint over real Postgres.

Exercises the composite-score aggregation and the 12-week trend against a live
database, with the DB session and auth dependencies overridden onto the test
engine and a fixed org.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from src.auth import CurrentUser, get_current_user
from src.db.session import get_db
from src.main import app
from src.models.appliance import Appliance, Org
from src.models.test_run import TestRun
from src.models.workload import Workload

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_readiness_endpoint_composite_and_trend(db_engine, db_session):
    org_id = uuid.uuid4()
    appliance_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="Readiness Org"))
    db_session.add(Appliance(id=appliance_id, org_id=org_id, name="ap-1",
                             mtls_thumbprint="t", status="active"))
    await db_session.commit()

    wls = []
    for i in range(2):
        wl = Workload(appliance_id=appliance_id, name=f"wl-{i}", platform="vmware",
                      rto_target_mins=30, rpo_target_mins=60)
        db_session.add(wl)
        wls.append(wl)
    await db_session.commit()

    now = datetime.now(UTC)
    db_session.add(TestRun(workload_id=wls[0].id, status="passed", started_at=now,
                           completed_at=now, rto_actual_mins=15, rpo_actual_mins=20,
                           readiness_score=95))
    db_session.add(TestRun(workload_id=wls[1].id, status="failed", started_at=now,
                           completed_at=now, rto_actual_mins=45, rpo_actual_mins=10,
                           readiness_score=40))
    await db_session.commit()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="auth0|test", org_id=org_id, email="t@example.com", role="admin"
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/dashboard/readiness")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["workloads_total"] == 2
    assert data["workloads_tested"] == 2
    assert data["workloads_passing"] == 1
    # 1 of 2 workloads tested, 1 passing, 100% RTO/RPO among the passed run.
    assert 0 < data["overall_score"] <= 100
    assert len(data["trend"]) == 12
    assert data["trend"][-1]["runs"] == 2
    assert data["trend"][-1]["pass_rate"] == 50
