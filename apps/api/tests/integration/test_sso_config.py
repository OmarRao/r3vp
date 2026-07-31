# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Integration tests for SSO config CRUD over real Postgres.

Covers the OIDC config upsert/read/toggle path (secret is write-only and never
returned), plus permission gating and per-protocol validation. The live IdP
handshake (/oidc/login, /oidc/callback) is NOT tested here - it requires a real
IdP; its pure inner logic is covered by tests/test_oidc_service.py.
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
from src.models.rbac import SsoConfig

pytestmark = pytest.mark.integration


def _client(db_session, org_id, role):
    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="auth0|sso-admin", org_id=org_id, email="admin@example.com", role=role
    )
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _clear():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_oidc_config_upsert_read_and_secret_is_write_only(db_engine, db_session):
    org_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="SSO Org"))
    await db_session.commit()

    payload = {
        "protocol": "oidc",
        "provider": "oidc",
        "oidc_issuer": "https://idp.example.com/",
        "oidc_client_id": "client-abc",
        "oidc_client_secret": "super-secret",
        "oidc_redirect_uri": "https://app.r3vp.io/callback",
        "oidc_scopes": ["openid", "email", "profile"],
        "attribute_mapping": {"email": "upn", "role": "app_role"},
    }
    try:
        async with _client(db_session, org_id, "owner") as client:
            put = await client.put("/v1/sso", json=payload)
            get = await client.get("/v1/sso")
    finally:
        _clear()

    assert put.status_code == 200, put.text
    body = put.json()
    assert body["protocol"] == "oidc"
    assert body["oidc_client_id"] == "client-abc"
    assert body["oidc_client_secret_set"] is True
    # Secret must never be echoed back.
    assert "oidc_client_secret" not in body

    got = get.json()
    assert got["configured"] is True
    assert got["oidc_issuer"] == "https://idp.example.com/"
    assert got["oidc_scopes"] == ["openid", "email", "profile"]

    # Persisted secret is intact in the DB even though it is never returned.
    row = await db_session.scalar(select(SsoConfig).where(SsoConfig.org_id == org_id))
    assert row is not None
    assert row.oidc_client_secret == "super-secret"


@pytest.mark.asyncio
async def test_oidc_upsert_preserves_secret_when_omitted(db_engine, db_session):
    org_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="SSO Org 2"))
    await db_session.commit()

    base = {
        "protocol": "oidc",
        "provider": "oidc",
        "oidc_issuer": "https://idp.example.com/",
        "oidc_client_id": "client-abc",
        "oidc_redirect_uri": "https://app/callback",
    }
    try:
        async with _client(db_session, org_id, "owner") as client:
            await client.put("/v1/sso", json={**base, "oidc_client_secret": "s1"})
            # Second upsert without a secret must not wipe the stored one.
            await client.put("/v1/sso", json=base)
    finally:
        _clear()

    row = await db_session.scalar(select(SsoConfig).where(SsoConfig.org_id == org_id))
    assert row is not None and row.oidc_client_secret == "s1"


@pytest.mark.asyncio
async def test_toggle_flips_enabled(db_engine, db_session):
    org_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="SSO Org 3"))
    await db_session.commit()

    payload = {
        "protocol": "oidc",
        "provider": "oidc",
        "oidc_issuer": "https://idp/",
        "oidc_client_id": "c",
        "oidc_redirect_uri": "https://cb",
    }
    try:
        async with _client(db_session, org_id, "owner") as client:
            await client.put("/v1/sso", json=payload)
            first = await client.patch("/v1/sso/toggle")
            second = await client.patch("/v1/sso/toggle")
    finally:
        _clear()

    assert first.json()["enabled"] is False
    assert second.json()["enabled"] is True


@pytest.mark.asyncio
async def test_oidc_config_missing_required_field_is_400(db_engine, db_session):
    org_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="SSO Org 4"))
    await db_session.commit()
    try:
        async with _client(db_session, org_id, "owner") as client:
            resp = await client.put("/v1/sso", json={"protocol": "oidc", "provider": "oidc"})
    finally:
        _clear()
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sso_manage_permission_required(db_engine, db_session):
    org_id = uuid.uuid4()
    db_session.add(Org(id=org_id, name="SSO Org 5"))
    await db_session.commit()
    # admin role deliberately lacks sso:manage.
    try:
        async with _client(db_session, org_id, "admin") as client:
            resp = await client.get("/v1/sso")
    finally:
        _clear()
    assert resp.status_code == 403
