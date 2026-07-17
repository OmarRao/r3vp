"""Integration tests: MSSP partner provisioning over real Postgres.

Guards the fix for the modeling gap where the console used the caller's org id
directly as `mssp_id` (an FK to mssp_partners.id), which FK-violated on insert
and leaked every partner's customers to every caller.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.auth import CurrentUser, get_current_user
from src.db.session import get_db
from src.main import app
from src.models.appliance import Org
from src.services.mssp_provisioning import get_or_create_partner

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_get_or_create_partner_is_idempotent(db_engine, db_session):
    org_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="MSSP Org"))
    await db_session.commit()

    p1 = await get_or_create_partner(db_session, org_id)
    await db_session.commit()
    p2 = await get_or_create_partner(db_session, org_id)

    assert p1.id == p2.id
    assert p1.org_id == org_id


def _auth(org_id):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="auth0|t", org_id=org_id, email="t@example.com", role="owner"
    )


@pytest.mark.asyncio
async def test_add_customer_then_list_is_scoped(db_engine, db_session):
    partner_a = uuid.uuid4()
    partner_b = uuid.uuid4()
    db_session.add(Org(id=partner_a, name="Partner A"))
    db_session.add(Org(id=partner_b, name="Partner B"))
    await db_session.commit()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    try:
        # Partner A adds a customer - no pre-existing partner row needed.
        _auth(partner_a)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            add = await client.post("/v1/mssp/customers", json={
                "org_id": str(uuid.uuid4()),
                "display_name": "Acme (A)",
                "tier": "premium",
            })
            assert add.status_code == 201, add.text
            list_a = await client.get("/v1/mssp/customers")

        # Partner B sees none of A's customers (falls back to demo mock only
        # because it has zero real customers).
        _auth(partner_b)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            list_b = await client.get("/v1/mssp/customers")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    names_a = [c["display_name"] for c in list_a.json()]
    assert "Acme (A)" in names_a
    # Partner B's response must not contain A's real customer.
    assert "Acme (A)" not in [c["display_name"] for c in list_b.json()]
