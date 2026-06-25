"""Onboarding wizard API: session management and step progression."""
from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.onboarding import OnboardingSession
from src.services.onboarding import STEPS, get_step_definition, compute_progress

router = APIRouter()


class UpdateStepRequest(BaseModel):
    step_id: str
    data: dict


@router.get("")
async def get_onboarding_status(user: AuthUser, db: AsyncSession = Depends(get_db)):
    session = await db.scalar(
        select(OnboardingSession).where(OnboardingSession.org_id == user.org_id)
    )
    if not session:
        session = OnboardingSession(
            org_id=user.org_id,
            created_by=getattr(user, "user_id", None),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    progress = compute_progress(session.step_data)
    current_def = get_step_definition(session.current_step)

    return {
        "current_step": session.current_step,
        "current_step_def": current_def,
        "completed": session.completed,
        "dismissed": session.dismissed,
        "progress": progress,
        "step_data": session.step_data,
        "steps": STEPS,
    }


@router.post("/step")
async def update_step(body: UpdateStepRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    session = await db.scalar(
        select(OnboardingSession).where(OnboardingSession.org_id == user.org_id)
    )
    if not session:
        raise HTTPException(404, "Onboarding session not found")

    step_def = next((s for s in STEPS if s["id"] == body.step_id), None)
    if not step_def:
        raise HTTPException(400, f"Unknown step_id: {body.step_id}")

    merged = {**session.step_data, **body.data}
    session.step_data = merged

    if step_def["step"] >= session.current_step:
        next_step = min(step_def["step"] + 1, len(STEPS))
        session.current_step = next_step

    if session.current_step >= len(STEPS) and not session.completed:
        progress = compute_progress(session.step_data)
        if progress["percent"] >= 80:
            session.completed = True
            session.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(session)
    return {"current_step": session.current_step, "completed": session.completed, "step_data": session.step_data}


@router.post("/dismiss")
async def dismiss_onboarding(user: AuthUser, db: AsyncSession = Depends(get_db)):
    session = await db.scalar(
        select(OnboardingSession).where(OnboardingSession.org_id == user.org_id)
    )
    if not session:
        raise HTTPException(404, "Onboarding session not found")
    session.dismissed = True
    await db.commit()
    return {"dismissed": True}


@router.post("/reset")
async def reset_onboarding(user: AuthUser, db: AsyncSession = Depends(get_db)):
    session = await db.scalar(
        select(OnboardingSession).where(OnboardingSession.org_id == user.org_id)
    )
    if not session:
        raise HTTPException(404, "Onboarding session not found")
    session.current_step = 1
    session.completed = False
    session.dismissed = False
    session.completed_at = None
    session.step_data = {}
    await db.commit()
    return {"reset": True}
