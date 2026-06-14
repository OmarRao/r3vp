"""Appliance channel — called by the on-prem appliance via mTLS, not by portal users."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db

router = APIRouter()


class RegisterRequest(BaseModel):
    appliance_id: str
    org_id: str


class HeartbeatRequest(BaseModel):
    appliance_id: str
    version: str


class InventorySyncRequest(BaseModel):
    run_id: str
    vms: list[dict]


class ProgressRequest(BaseModel):
    step: str
    status: str
    detail: dict = {}


class ResultRequest(BaseModel):
    passed: bool
    rto_actual_mins: int
    rpo_actual_mins: int
    readiness_score: int
    failure_reason: str | None = None


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    # In production: verify mTLS cert thumbprint matches registered appliance
    return {"status": "registered", "appliance_id": req.appliance_id}


@router.post("/heartbeat")
async def heartbeat(req: HeartbeatRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return {"status": "ok", "server_time": datetime.now(timezone.utc).isoformat()}


@router.post("/inventory/sync")
async def inventory_sync(req: InventorySyncRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return {"status": "accepted", "vm_count": len(req.vms)}


@router.post("/test-runs/{run_id}/progress")
async def post_progress(run_id: str, req: ProgressRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return {"status": "accepted"}


@router.post("/test-runs/{run_id}/result")
async def post_result(run_id: str, req: ResultRequest, db: AsyncSession = Depends(get_db)) -> dict:
    return {"status": "accepted"}


@router.post("/test-runs/{run_id}/evidence")
async def upload_evidence(
    run_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # In production: stream to S3 under the run's evidence prefix
    return {"status": "accepted", "filename": file.filename}


@router.get("/commands")
async def get_commands(db: AsyncSession = Depends(get_db)) -> dict:
    # Long-poll endpoint — returns pending test-run triggers for this appliance
    return {"commands": []}
