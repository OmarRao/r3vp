"""Integration test: /v1/insights/risk-ranking over real Postgres.

Seeds workloads with differing recency / RTO / failure profiles and asserts the
endpoint ranks them by real computed risk.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

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
async def test_risk_ranking_uses_real_data(db_engine, db_session):
    org_id = uuid.uuid4()
    appliance_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="Risk Org"))
    db_session.add(Appliance(id=appliance_id, org_id=org_id, name="ap-1",
                             mtls_thumbprint="t", status="active"))
    await db_session.commit()

    now = datetime.now(UTC)

    # High risk: RTO over target + a failure.
    risky = Workload(appliance_id=appliance_id, name="risky", platform="vmware",
                     rto_target_mins=60, rpo_target_mins=60)
    # Low risk: well within RTO, recent, no failures.
    healthy = Workload(appliance_id=appliance_id, name="healthy", platform="vmware",
                       rto_target_mins=60, rpo_target_mins=60)
    db_session.add_all([risky, healthy])
    await db_session.commit()

    db_session.add(TestRun(workload_id=risky.id, status="failed", started_at=now - timedelta(days=2),
                           completed_at=now - timedelta(days=2), rto_actual_mins=90, rpo_actual_mins=10))
    db_session.add(TestRun(workload_id=risky.id, status="passed", started_at=now,
                           completed_at=now, rto_actual_mins=58, rpo_actual_mins=10))
    db_session.add(TestRun(workload_id=healthy.id, status="passed", started_at=now,
                           completed_at=now, rto_actual_mins=10, rpo_actual_mins=5))
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
            resp = await client.get("/v1/insights/risk-ranking")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    data = resp.json()
    ranked = data["workloads"]
    assert len(ranked) == 2
    # Highest risk first, and the risky workload outranks the healthy one.
    by_name = {w["workload"]: w for w in ranked}
    assert by_name["risky"]["risk_score"] > by_name["healthy"]["risk_score"]
    assert ranked[0]["workload"] == "risky"
