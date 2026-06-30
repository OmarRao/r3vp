"""SAML 2.0 SSO configuration endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.rbac import SsoConfig
from src.services.rbac import require_permission

router = APIRouter()

VALID_PROVIDERS = {"okta", "azure_ad", "google", "ping", "generic_saml"}


class SsoConfigRequest(BaseModel):
    provider: str
    entity_id: str
    sso_url: str
    certificate: str
    attribute_mapping: dict = {}


@router.get("")
async def get_sso_config(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "sso:manage")
    config = await db.scalar(select(SsoConfig).where(SsoConfig.org_id == user.org_id))
    if not config:
        return {"configured": False}
    return {
        "configured": True,
        "provider": config.provider,
        "entity_id": config.entity_id,
        "sso_url": config.sso_url,
        "enabled": config.enabled,
        "attribute_mapping": config.attribute_mapping,
    }


@router.put("")
async def upsert_sso_config(body: SsoConfigRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "sso:manage")
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(400, f"provider must be one of: {', '.join(sorted(VALID_PROVIDERS))}")

    config = await db.scalar(select(SsoConfig).where(SsoConfig.org_id == user.org_id))
    if config:
        config.provider = body.provider
        config.entity_id = body.entity_id
        config.sso_url = body.sso_url
        config.certificate = body.certificate
        config.attribute_mapping = body.attribute_mapping
    else:
        config = SsoConfig(
            org_id=user.org_id,
            provider=body.provider,
            entity_id=body.entity_id,
            sso_url=body.sso_url,
            certificate=body.certificate,
            attribute_mapping=body.attribute_mapping,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)
    return {"provider": config.provider, "enabled": config.enabled}


@router.patch("/toggle")
async def toggle_sso(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "sso:manage")
    config = await db.scalar(select(SsoConfig).where(SsoConfig.org_id == user.org_id))
    if not config:
        raise HTTPException(404, "SSO not configured")
    config.enabled = not config.enabled
    await db.commit()
    return {"enabled": config.enabled}
