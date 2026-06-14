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

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.config import settings

_bearer = HTTPBearer()


class CurrentUser(BaseModel):
    sub: str
    org_id: uuid.UUID
    email: str = ""


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Fetch JWKS from Auth0 (cached per process lifetime)."""
    url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _decode_token(token: str) -> dict:
    jwks = _get_jwks()
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token header: {exc}")

    rsa_key = {}
    for key in jwks.get("keys", []):
        if key.get("kid") == unverified_header.get("kid"):
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            break

    if not rsa_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unable to find matching JWKS key")

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Token validation failed: {exc}")

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
    except ValueError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid org_id in token")

    return CurrentUser(
        sub=payload["sub"],
        org_id=org_id,
        email=payload.get("email", ""),
    )


# Convenience alias for use in route signatures
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
