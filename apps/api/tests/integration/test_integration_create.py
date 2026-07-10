"""Integration test: creating an outbound integration over real Postgres.

Verifies a valid config persists (201) and that created_by resolves to the local
users.id (the resolve_local_user_id fix), not None.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.auth import CurrentUser, get_current_user
from src.db.session import get_db
from src.main import app
from src.models.appliance import Org
from src.models.integration import Integration
from src.models.test_run import User

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_create_integration_persists_and_sets_created_by(db_engine, db_session):
    org_id = uuid.uuid4()
    sub = "auth0|creator"
    db_session.add(Org(id=org_id, name="Int Org"))
    user_row = User(org_id=org_id, auth0_sub=sub, email="c@example.com", role="admin")
    db_session.add(user_row)
    await db_session.commit()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub=sub, org_id=org_id, email="c@example.com", role="admin"
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/integrations", json={
                "integration_type": "sentinel",
                "name": "SIEM",
                "config": {"workspace_id": "w1", "shared_key": "k1"},
                "trigger_events": ["threat_detected"],
            })
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 201

    row = await db_session.scalar(select(Integration).where(Integration.org_id == org_id))
    assert row is not None
    assert row.integration_type == "sentinel"
    # created_by resolved to the local user id (was always None before the fix).
    assert row.created_by == user_row.id
