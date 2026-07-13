"""Integration test: /v1/mssp/billing over real Postgres.

Also guards that the MSSP router is reachable (its permissions were previously
absent from the RBAC catalog, 403-ing every role including owner).
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
from src.models.mssp import MsspCustomerOrg, MsspPartner
from src.models.test_run import TestRun
from src.models.workload import Workload

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_mssp_billing_meters_customer_usage(db_engine, db_session):
    partner_org_id = uuid.uuid4()   # the MSSP partner (the authenticated user's org)
    customer_org_id = uuid.uuid4()  # a managed customer org
    appliance_id = uuid.uuid4()

    db_session.add(Org(id=partner_org_id, name="Partner"))
    db_session.add(Org(id=customer_org_id, name="Customer"))
    # The code treats MsspCustomerOrg.mssp_id as the partner's org id; create a
    # matching MsspPartner row first so the FK is satisfied.
    db_session.add(MsspPartner(id=partner_org_id, name="Partner MSSP", slug="partner-mssp"))
    db_session.add(Appliance(id=appliance_id, org_id=customer_org_id, name="ap",
                             mtls_thumbprint="t", status="active"))
    await db_session.commit()
    db_session.add(MsspCustomerOrg(mssp_id=partner_org_id, org_id=customer_org_id,
                                   display_name="Acme", industry="Tech", tier="premium"))
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
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="auth0|t", org_id=partner_org_id, email="t@example.com", role="admin"
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/mssp/billing?period_days=30")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200  # not 403 (RBAC catalog now has mssp:read)
    data = resp.json()
    assert data["summary"]["customer_count"] == 1
    assert data["summary"]["total_workloads"] == 1
    assert data["summary"]["total_test_runs"] == 1
    item = data["line_items"][0]
    assert item["customer"] == "Acme"
    assert item["tier"] == "premium"
    # premium: base 200 + 1*8.00 + 1*0.75 = 208.75
    assert item["total"] == 208.75
