# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Regression tests for two silent empty-result bugs caught by mypy.

Both endpoints built a filter from a Python boolean expression instead of a
SQL predicate, so the query became `WHERE ... AND false` and always returned
an empty list:

- team.list_invites used `OrgInvite.accepted_at is None` (Python `is`)
- api_keys.list_keys used `not ApiKey.revoked` (Python `not`)
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from src.auth import CurrentUser, get_current_user
from src.db.session import get_db
from src.main import app
from src.models.appliance import Org
from src.models.rbac import ApiKey, OrgInvite, Role
from src.models.test_run import User

pytestmark = pytest.mark.integration


def _auth(org_id):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="auth0|t", org_id=org_id, email="t@example.com", role="owner"
    )


@pytest.mark.asyncio
async def test_list_api_keys_returns_active_keys(db_engine, db_session):
    org_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="Org"))
    user = User(org_id=org_id, auth0_sub="auth0|u", email="u@example.com", role="owner")
    db_session.add(user)
    await db_session.commit()

    db_session.add(ApiKey(org_id=org_id, name="active-key", key_prefix="r3vp_ab",
                          key_hash="h1", scopes=["read"], created_by=user.id, revoked=False))
    db_session.add(ApiKey(org_id=org_id, name="revoked-key", key_prefix="r3vp_cd",
                          key_hash="h2", scopes=["read"], created_by=user.id, revoked=True))
    await db_session.commit()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    _auth(org_id)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/api-keys")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    names = [k["name"] for k in resp.json()]
    assert names == ["active-key"]  # the fix: not empty, and revoked excluded


@pytest.mark.asyncio
async def test_list_invites_returns_pending_invites(db_engine, db_session):
    org_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="Org"))
    inviter = User(org_id=org_id, auth0_sub="auth0|inv", email="inv@example.com", role="owner")
    role = Role(org_id=org_id, name="viewer", description="", permissions=[], is_system=False)
    db_session.add_all([inviter, role])
    await db_session.commit()

    db_session.add(OrgInvite(org_id=org_id, email="new@example.com", role_id=role.id,
                             token="tok-123", invited_by=inviter.id,
                             expires_at=datetime.now(UTC) + timedelta(days=7),
                             accepted_at=None))
    await db_session.commit()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    _auth(org_id)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/v1/team/invites")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    emails = [i["email"] for i in resp.json()]
    assert "new@example.com" in emails  # the fix: not empty
