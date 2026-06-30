"""Auth0 JWT verification for portal-facing routes.

Verifies the Bearer token against Auth0's JWKS endpoint, extracts the
org_id and user sub, and provides a FastAPI dependency that injects a
CurrentUser into any portal route.

Appliance routes use mTLS instead — they do NOT use this dependency.
"""
from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient
from pydantic import BaseModel

from src.config import settings

_bearer = HTTPBearer()


class CurrentUser(BaseModel):
    sub: str
    org_id: uuid.UUID
    email: str = ""
    role: str = "admin"


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient:
    """JWKS client for Auth0 (caches signing keys per process lifetime)."""
    url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    return PyJWKClient(url)


def _decode_token(token: str) -> dict:
    try:
        signing_key = _jwk_client().get_signing_key_from_jwt(token)
    except (InvalidTokenError, jwt.PyJWKClientError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token header: {exc}") from exc

    try:
        payload: dict = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Token validation failed: {exc}") from exc

    return payload


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> CurrentUser:
    payload = _decode_token(credentials.credentials)

    # Auth0 stores org_id in a custom namespace claim
    org_raw = payload.get("https://r3vp.io/org_id") or payload.get("org_id")
    if not org_raw:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token missing org_id claim")

    try:
        org_id = uuid.UUID(str(org_raw))
    except ValueError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid org_id in token") from exc

    return CurrentUser(
        sub=payload["sub"],
        org_id=org_id,
        email=payload.get("email", ""),
    )


# Convenience alias for use in route signatures
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Raise 403 if user is not an admin."""
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user


AdminUser = Annotated[CurrentUser, Depends(require_admin)]
