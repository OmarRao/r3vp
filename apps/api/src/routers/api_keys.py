"""API key management for programmatic/service account access."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.rbac import ApiKey
from src.services.rbac import PERMISSIONS, require_permission

router = APIRouter()

VALID_SCOPES = set(PERMISSIONS.keys())


class CreateKeyRequest(BaseModel):
    name: str
    scopes: list[str]
    expires_days: int | None = None


@router.get("")
async def list_keys(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "api_keys:read")
    rows = await db.execute(
        select(ApiKey).where(ApiKey.org_id == user.org_id, not ApiKey.revoked).order_by(ApiKey.created_at.desc())
    )
    return [
        {
            "id": str(k.id),
            "name": k.name,
            "prefix": k.key_prefix,
            "scopes": k.scopes,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "created_at": k.created_at.isoformat(),
        }
        for k in rows.scalars().all()
    ]


@router.post("", status_code=201)
async def create_key(body: CreateKeyRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "api_keys:write")

    invalid = [s for s in body.scopes if s not in VALID_SCOPES]
    if invalid:
        raise HTTPException(400, f"Invalid scopes: {invalid}")

    raw, prefix, digest = ApiKey.generate()

    expires_at = None
    if body.expires_days:
        from datetime import timedelta
        expires_at = datetime.now(UTC) + timedelta(days=body.expires_days)

    key = ApiKey(
        org_id=user.org_id,
        name=body.name,
        key_prefix=prefix,
        key_hash=digest,
        scopes=body.scopes,
        expires_at=expires_at,
        created_by=getattr(user, "user_id", None),
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)

    return {
        "id": str(key.id),
        "name": key.name,
        "key": raw,
        "prefix": prefix,
        "scopes": key.scopes,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "created_at": key.created_at.isoformat(),
        "_note": "Store this key securely. It will not be shown again.",
    }


@router.delete("/{key_id}", status_code=204)
async def revoke_key(key_id: uuid.UUID, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "api_keys:write")
    key = await db.scalar(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == user.org_id)
    )
    if not key:
        raise HTTPException(404, "API key not found")
    key.revoked = True
    await db.commit()
