# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""SSO configuration and OIDC login endpoints.

Two protocols are supported per org (one active config each): SAML 2.0 (legacy
columns: entity_id / sso_url / certificate) and OIDC (issuer / client_id /
client_secret / redirect_uri / scopes).

Verification boundary:
  * The config CRUD endpoints and the pure OIDC helpers (state/nonce, URL build,
    id_token validation, claim mapping) are covered by tests.
  * The OIDC ``/oidc/login`` and ``/oidc/callback`` endpoints perform live HTTP
    (discovery document, token-endpoint code exchange, JWKS fetch) against a
    real IdP and therefore cannot be exercised end-to-end without one. Their
    security-critical inner logic is delegated to ``src.services.oidc`` and IS
    unit tested; only the network handshake is left unverified here.
"""
from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.rbac import SsoConfig
from src.services import oidc
from src.services.rbac import require_permission

router = APIRouter()

VALID_PROVIDERS = {"okta", "azure_ad", "google", "ping", "generic_saml", "oidc"}
VALID_PROTOCOLS = {"saml", "oidc"}


class SsoConfigRequest(BaseModel):
    protocol: str = "saml"
    provider: str
    attribute_mapping: dict = {}
    # SAML
    entity_id: str | None = None
    sso_url: str | None = None
    certificate: str | None = None
    # OIDC
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_redirect_uri: str | None = None
    oidc_scopes: list[str] = []


def _validate_request(body: SsoConfigRequest) -> None:
    if body.protocol not in VALID_PROTOCOLS:
        raise HTTPException(400, f"protocol must be one of: {', '.join(sorted(VALID_PROTOCOLS))}")
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(400, f"provider must be one of: {', '.join(sorted(VALID_PROVIDERS))}")
    if body.protocol == "saml":
        missing = [f for f in ("entity_id", "sso_url", "certificate") if not getattr(body, f)]
        if missing:
            raise HTTPException(400, f"SAML config requires: {', '.join(missing)}")
    else:  # oidc
        required = ("oidc_issuer", "oidc_client_id", "oidc_redirect_uri")
        missing = [f for f in required if not getattr(body, f)]
        if missing:
            raise HTTPException(400, f"OIDC config requires: {', '.join(missing)}")


def _serialize(config: SsoConfig) -> dict:
    """Public representation. The OIDC client secret is intentionally omitted."""
    return {
        "configured": True,
        "protocol": config.protocol,
        "provider": config.provider,
        "enabled": config.enabled,
        "attribute_mapping": config.attribute_mapping,
        # SAML
        "entity_id": config.entity_id,
        "sso_url": config.sso_url,
        # OIDC (secret excluded; expose whether one is set)
        "oidc_issuer": config.oidc_issuer,
        "oidc_client_id": config.oidc_client_id,
        "oidc_redirect_uri": config.oidc_redirect_uri,
        "oidc_scopes": config.oidc_scopes,
        "oidc_client_secret_set": bool(config.oidc_client_secret),
    }


@router.get("")
async def get_sso_config(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "sso:manage")
    config = await db.scalar(select(SsoConfig).where(SsoConfig.org_id == user.org_id))
    if not config:
        return {"configured": False}
    return _serialize(config)


@router.put("")
async def upsert_sso_config(body: SsoConfigRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "sso:manage")
    _validate_request(body)

    config = await db.scalar(select(SsoConfig).where(SsoConfig.org_id == user.org_id))
    if config is None:
        config = SsoConfig(org_id=user.org_id)
        db.add(config)

    config.protocol = body.protocol
    config.provider = body.provider
    config.attribute_mapping = body.attribute_mapping
    config.entity_id = body.entity_id
    config.sso_url = body.sso_url
    config.certificate = body.certificate
    config.oidc_issuer = body.oidc_issuer
    config.oidc_client_id = body.oidc_client_id
    # Preserve an existing secret when the caller omits it (write-only field).
    if body.oidc_client_secret:
        config.oidc_client_secret = body.oidc_client_secret
    config.oidc_redirect_uri = body.oidc_redirect_uri
    config.oidc_scopes = body.oidc_scopes or oidc.DEFAULT_SCOPES

    await db.commit()
    await db.refresh(config)
    return _serialize(config)


@router.patch("/toggle")
async def toggle_sso(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "sso:manage")
    config = await db.scalar(select(SsoConfig).where(SsoConfig.org_id == user.org_id))
    if not config:
        raise HTTPException(404, "SSO not configured")
    config.enabled = not config.enabled
    await db.commit()
    return {"enabled": config.enabled}


# --------------------------------------------------------------------------
# OIDC login flow (network-facing; E2E requires a real IdP - see module docs).
# --------------------------------------------------------------------------


async def _fetch_discovery(issuer: str) -> dict:
    """Fetch the OIDC discovery document. Network I/O; not unit tested."""
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data: dict = resp.json()
        return data


@router.get("/oidc/login")
async def oidc_login(
    org_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Initiate OIDC login: return the authorization redirect URL + state/nonce.

    Public (pre-authentication) endpoint. The caller must persist ``state`` and
    ``nonce`` and re-check them at the callback. The discovery fetch is live
    network I/O; the URL construction is the unit-tested pure helper.
    """
    config = await db.scalar(select(SsoConfig).where(SsoConfig.org_id == org_id))
    if not config or config.protocol != "oidc" or not config.enabled:
        raise HTTPException(404, "OIDC SSO not configured for this org")

    discovery = await _fetch_discovery(config.oidc_issuer or "")
    auth_req = oidc.build_authorization_url(
        authorization_endpoint=discovery["authorization_endpoint"],
        client_id=config.oidc_client_id or "",
        redirect_uri=config.oidc_redirect_uri or "",
        scopes=config.oidc_scopes or None,
    )
    return {
        "authorization_url": auth_req.url,
        "state": auth_req.state,
        "nonce": auth_req.nonce,
    }


class OidcCallbackRequest(BaseModel):
    org_id: uuid.UUID
    code: str
    nonce: str


@router.post("/oidc/callback")
async def oidc_callback(body: OidcCallbackRequest, db: AsyncSession = Depends(get_db)):
    """Exchange an authorization code and validate the returned id_token.

    Network I/O (token exchange + JWKS fetch) makes the full path E2E-untestable
    without a real IdP; the id_token validation and claim mapping it relies on
    are the unit-tested pure helpers in ``src.services.oidc``.
    """
    config = await db.scalar(select(SsoConfig).where(SsoConfig.org_id == body.org_id))
    if not config or config.protocol != "oidc" or not config.enabled:
        raise HTTPException(404, "OIDC SSO not configured for this org")

    issuer = config.oidc_issuer or ""
    discovery = await _fetch_discovery(issuer)

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            discovery["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": body.code,
                "redirect_uri": config.oidc_redirect_uri or "",
                "client_id": config.oidc_client_id or "",
                "client_secret": config.oidc_client_secret or "",
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()
        jwks_resp = await client.get(discovery["jwks_uri"])
        jwks_resp.raise_for_status()
        jwks = jwks_resp.json()

    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(400, "token response missing id_token")

    try:
        claims = oidc.validate_id_token(
            id_token,
            jwks,
            issuer=issuer,
            audience=config.oidc_client_id or "",
            nonce=body.nonce,
        )
        identity = oidc.map_claims_to_identity(claims, config.attribute_mapping)
    except oidc.OidcError as exc:
        raise HTTPException(401, str(exc)) from exc

    return {
        "subject": identity.subject,
        "email": identity.email,
        "role": identity.role,
    }
