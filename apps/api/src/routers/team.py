"""Team management: members, invites, roles."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.rbac import OrgInvite, OrgMember, Role
from src.services.rbac import SYSTEM_ROLES, require_permission

router = APIRouter()


class InviteRequest(BaseModel):
    email: str
    role_name: str


class MemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role_name: str
    joined_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


@router.get("/members")
async def list_members(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "team:read")
    rows = await db.execute(
        select(OrgMember, Role)
        .join(Role, OrgMember.role_id == Role.id)
        .where(OrgMember.org_id == user.org_id, OrgMember.is_active)
        .order_by(OrgMember.joined_at)
    )
    return [
        {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "role": r.name,
            "joined_at": m.joined_at.isoformat(),
            "is_active": m.is_active,
        }
        for m, r in rows.all()
    ]


@router.post("/invites", status_code=201)
async def invite_member(body: InviteRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "team:invite")
    if body.role_name not in SYSTEM_ROLES:
        raise HTTPException(400, f"role_name must be one of: {', '.join(SYSTEM_ROLES)}")
    if body.role_name == "owner":
        raise HTTPException(400, "Cannot invite as owner")

    role = await db.scalar(
        select(Role).where(Role.name == body.role_name, Role.is_system)
    )
    if not role:
        raise HTTPException(400, f"Role not found: {body.role_name}")

    invite = OrgInvite(
        org_id=user.org_id,
        email=body.email,
        role_id=role.id,
        token=OrgInvite.generate_token(),
        invited_by=getattr(user, "user_id", None),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return {"id": str(invite.id), "email": invite.email, "token": invite.token, "expires_at": invite.expires_at.isoformat()}


@router.get("/invites")
async def list_invites(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "team:read")
    rows = await db.execute(
        select(OrgInvite)
        .where(OrgInvite.org_id == user.org_id, OrgInvite.accepted_at is None)
        .order_by(OrgInvite.created_at.desc())
    )
    return [
        {"id": str(i.id), "email": i.email, "expires_at": i.expires_at.isoformat(), "created_at": i.created_at.isoformat()}
        for i in rows.scalars().all()
    ]


@router.patch("/members/{member_id}/role")
async def update_member_role(
    member_id: uuid.UUID,
    body: dict,
    user: AuthUser,
    db: AsyncSession = Depends(get_db),
):
    require_permission(getattr(user, "permissions", []), "team:manage")
    role_name = body.get("role_name")
    if role_name not in SYSTEM_ROLES or role_name == "owner":
        raise HTTPException(400, "Invalid role_name")

    member = await db.scalar(
        select(OrgMember).where(OrgMember.id == member_id, OrgMember.org_id == user.org_id)
    )
    if not member:
        raise HTTPException(404, "Member not found")

    role = await db.scalar(select(Role).where(Role.name == role_name, Role.is_system))
    if not role:
        raise HTTPException(400, "Role not found")

    member.role_id = role.id
    await db.commit()
    return {"id": str(member.id), "role": role_name}


@router.delete("/members/{member_id}", status_code=204)
async def remove_member(member_id: uuid.UUID, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "team:manage")
    member = await db.scalar(
        select(OrgMember).where(OrgMember.id == member_id, OrgMember.org_id == user.org_id)
    )
    if not member:
        raise HTTPException(404, "Member not found")
    member.is_active = False
    await db.commit()
