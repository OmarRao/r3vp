from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.auth import AuthUser, AdminUser
from src.db.session import get_db
from src.models.test_run import User

router = APIRouter()


class ProvisionUserRequest(BaseModel):
    auth0_sub: str
    email: str
    role: str = "viewer"


class UserResponse(BaseModel):
    id: uuid.UUID
    auth0_sub: str
    email: str
    role: str
    model_config = {"from_attributes": True}


@router.post("/provision", response_model=UserResponse)
async def provision_user(
    req: ProvisionUserRequest,
    user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> User:
    if req.role not in ("admin", "viewer"):
        raise HTTPException(400, "role must be admin or viewer")
    stmt = (
        pg_insert(User)
        .values(org_id=user.org_id, auth0_sub=req.auth0_sub, email=req.email, role=req.role)
        .on_conflict_do_update(
            index_elements=["auth0_sub"],
            set_={"email": req.email, "role": req.role},
        )
        .returning(User)
    )
    result = await db.execute(stmt)
    provisioned = result.scalar_one()
    await db.commit()
    return provisioned


@router.get("/me", response_model=UserResponse)
async def get_me(user: AuthUser, db: AsyncSession = Depends(get_db)) -> dict:
    return {"id": uuid.uuid4(), "auth0_sub": user.sub, "email": user.email, "role": user.role}
