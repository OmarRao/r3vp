"""Integration test: /v1/insights/query answers from live org data."""
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


async def _ask(org_id, question):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="auth0|t", org_id=org_id, email="t@example.com", role="admin"
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/v1/insights/query", json={"query": question})
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_nl_query_uses_live_counts(db_engine, db_session):
    org_id = uuid.uuid4()
    appliance_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="NL Org"))
    db_session.add(Appliance(id=appliance_id, org_id=org_id, name="ap",
                             mtls_thumbprint="t", status="active"))
    await db_session.commit()
    wl = Workload(appliance_id=appliance_id, name="vm1", platform="vmware",
                  rto_target_mins=60, rpo_target_mins=60)
    db_session.add(wl)
    await db_session.commit()
    db_session.add(TestRun(workload_id=wl.id, status="passed", started_at=datetime.now(UTC),
                           completed_at=datetime.now(UTC), rto_actual_mins=20, rpo_actual_mins=10))
    await db_session.commit()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    try:
        resp = await _ask(org_id, "how many workloads are there?")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200  # not 403 (permission fix) and no mock context
    answer = resp.json()["answer"]
    # 1 real workload, 1 tested -> answer reflects live counts, not the old mock (47).
    assert "1 workload" in answer and "47" not in answer
