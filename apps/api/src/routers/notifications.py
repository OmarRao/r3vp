from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AdminUser, AuthUser
from src.db.session import get_db
from src.models.notification import NotificationChannel

router = APIRouter()


class CreateChannelRequest(BaseModel):
    name: str
    channel_type: str  # email | slack | teams
    destination: str
    events: list[str] = ["test_failed", "rto_breach", "rpo_breach"]


class ChannelResponse(BaseModel):
    id: uuid.UUID
    name: str
    channel_type: str
    destination: str
    events: list[str]
    enabled: bool
    model_config = {"from_attributes": True}


@router.get("", response_model=list[ChannelResponse])
async def list_channels(user: AuthUser, db: AsyncSession = Depends(get_db)) -> list:
    rows = await db.execute(
        select(NotificationChannel).where(NotificationChannel.org_id == user.org_id)
    )
    return rows.scalars().all()


@router.post("", response_model=ChannelResponse, status_code=201)
async def create_channel(
    req: CreateChannelRequest,
    user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> NotificationChannel:
    if req.channel_type not in ("email", "slack", "teams"):
        raise HTTPException(400, "channel_type must be email, slack, or teams")
    ch = NotificationChannel(
        org_id=user.org_id,
        name=req.name,
        channel_type=req.channel_type,
        destination=req.destination,
        events=req.events,
    )
    db.add(ch)
    await db.commit()
    await db.refresh(ch)
    return ch


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: uuid.UUID,
    user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        delete(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.org_id == user.org_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(404, "Notification channel not found")
    await db.commit()
