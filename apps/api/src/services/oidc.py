# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Pure OIDC helper logic (no network, no database).

Everything network-facing (discovery document fetch, token-endpoint code
exchange, live JWKS retrieval) lives in the router so that the security-critical
logic here can be unit tested with a locally-signed JWT and an in-memory JWKS.

The functions here cover:
  * cryptographically random ``state`` / ``nonce`` generation,
  * building the authorization redirect URL,
  * validating an ``id_token`` (signature via JWKS, issuer, audience, expiry,
    and nonce), and
  * mapping validated claims to a local user identity + role.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from urllib.parse import urlencode

import jwt
from jwt import InvalidTokenError, PyJWKSet

DEFAULT_SCOPES = ["openid", "email", "profile"]


class OidcError(Exception):
    """Base class for OIDC validation failures (maps to HTTP 401/400)."""


class OidcValidationError(OidcError):
    """Raised when an id_token fails signature or claim validation."""


@dataclass
class AuthorizationRequest:
    """The result of initiating an OIDC login.

    ``state`` and ``nonce`` must be persisted (e.g. signed cookie / short-lived
    store) by the caller and checked again in the callback.
    """

    url: str
    state: str
    nonce: str


@dataclass
class OidcIdentity:
    """A local identity mapped out of validated id_token claims."""

    subject: str
    email: str
    role: str
    raw_claims: dict = field(default_factory=dict)


def generate_state() -> str:
    """Return a high-entropy, URL-safe anti-CSRF state token."""
    return secrets.token_urlsafe(32)


def generate_nonce() -> str:
    """Return a high-entropy, URL-safe replay-protection nonce."""
    return secrets.token_urlsafe(32)


def build_authorization_url(
    authorization_endpoint: str,
    client_id: str,
    redirect_uri: str,
    scopes: list[str] | None = None,
    *,
    state: str | None = None,
    nonce: str | None = None,
) -> AuthorizationRequest:
    """Build the OIDC authorization-code redirect URL.

    ``state`` / ``nonce`` are generated when not supplied so callers get fresh,
    unpredictable values by default. This function performs no I/O.
    """
    if not authorization_endpoint:
        raise OidcError("authorization_endpoint is required")
    if not client_id:
        raise OidcError("client_id is required")
    if not redirect_uri:
        raise OidcError("redirect_uri is required")

    state = state or generate_state()
    nonce = nonce or generate_nonce()
    scope_list = scopes or DEFAULT_SCOPES
    if "openid" not in scope_list:
        # OIDC requires the openid scope; add it rather than silently omitting.
        scope_list = ["openid", *scope_list]

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scope_list),
        "state": state,
        "nonce": nonce,
    }
    sep = "&" if "?" in authorization_endpoint else "?"
    url = f"{authorization_endpoint}{sep}{urlencode(params)}"
    return AuthorizationRequest(url=url, state=state, nonce=nonce)


def validate_id_token(
    id_token: str,
    jwks: dict,
    *,
    issuer: str,
    audience: str,
    nonce: str | None = None,
    leeway: int = 0,
) -> dict:
    """Validate an id_token against a JWKS and return its claims.

    Raises :class:`OidcValidationError` on any failure: unknown / missing signing
    key, bad signature, expired token, wrong issuer, wrong audience, or a nonce
    mismatch. ``leeway`` (seconds) is passed to the expiry check to tolerate
    small clock skew.
    """
    try:
        jwk_set = PyJWKSet.from_dict(jwks)
    except Exception as exc:  # malformed JWKS
        raise OidcValidationError(f"invalid JWKS: {exc}") from exc

    try:
        header = jwt.get_unverified_header(id_token)
    except InvalidTokenError as exc:
        raise OidcValidationError(f"malformed token header: {exc}") from exc

    kid = header.get("kid")
    signing_key = None
    for key in jwk_set.keys:
        if kid is None or key.key_id == kid:
            signing_key = key
            break
    if signing_key is None:
        raise OidcValidationError("no matching signing key for token kid")

    try:
        claims: dict = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            leeway=leeway,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except InvalidTokenError as exc:
        raise OidcValidationError(f"id_token validation failed: {exc}") from exc

    if nonce is not None and claims.get("nonce") != nonce:
        raise OidcValidationError("nonce mismatch")

    return claims


def map_claims_to_identity(
    claims: dict,
    attribute_mapping: dict | None = None,
    *,
    default_role: str = "viewer",
) -> OidcIdentity:
    """Map validated id_token claims to a local identity + role.

    ``attribute_mapping`` lets an org point at non-standard claim names, e.g.
    ``{"email": "upn", "role": "app_role"}``. The role claim value is lower-cased
    and falls back to ``default_role`` when absent or unrecognized upstream.
    """
    mapping = attribute_mapping or {}
    email_claim = mapping.get("email", "email")
    role_claim = mapping.get("role", "role")

    subject = str(claims.get("sub", "")).strip()
    if not subject:
        raise OidcValidationError("id_token missing sub claim")

    email = str(claims.get(email_claim, "")).strip()
    if not email:
        raise OidcValidationError(f"id_token missing email claim ({email_claim!r})")

    role_value = claims.get(role_claim)
    role = str(role_value).strip().lower() if role_value else default_role

    return OidcIdentity(subject=subject, email=email, role=role, raw_claims=claims)
