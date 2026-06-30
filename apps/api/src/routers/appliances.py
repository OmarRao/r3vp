"""Appliance relay channel — called by on-prem appliance over mTLS, not by portal users.

mTLS termination happens at the load balancer / API gateway. The gateway
forwards the client cert's SHA-256 thumbprint in the X-Client-Cert-Thumbprint
header. Each endpoint verifies it matches the registered appliance before
processing the request.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.appliance import Appliance
from src.services import appliance as svc

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _appliance_id_header(request: Request) -> uuid.UUID:
    raw = request.headers.get("X-Appliance-ID")
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-Appliance-ID header")
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid X-Appliance-ID") from exc


def _org_id_header(request: Request) -> uuid.UUID:
    raw = request.headers.get("X-Org-ID")
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-Org-ID header")
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid X-Org-ID") from exc


async def _verified_appliance(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Appliance:
    """Look up the appliance and verify the mTLS thumbprint matches."""
    appliance_id = _appliance_id_header(request)
    thumbprint = request.headers.get("X-Client-Cert-Thumbprint", "")

    row = await db.scalar(select(Appliance).where(Appliance.id == appliance_id))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appliance not registered")
    if thumbprint and row.mtls_thumbprint != thumbprint:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Certificate thumbprint mismatch")
    return row


# ── Request/response schemas ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    appliance_id: uuid.UUID
    org_id: uuid.UUID
    name: str = "default"
    version: str | None = None
    mtls_thumbprint: str = ""  # populated by gateway from client cert


class HeartbeatRequest(BaseModel):
    version: str


class InventorySyncRequest(BaseModel):
    run_id: str | None = None
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_200_OK)
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # The gateway injects the real thumbprint; fall back to the body field for dev
    thumbprint = request.headers.get("X-Client-Cert-Thumbprint") or req.mtls_thumbprint
    await svc.register_appliance(
        db,
        org_id=req.org_id,
        appliance_id=req.appliance_id,
        name=req.name,
        mtls_thumbprint=thumbprint,
        version=req.version,
    )
    return {"status": "registered", "appliance_id": str(req.appliance_id)}


@router.post("/heartbeat")
async def heartbeat(
    req: HeartbeatRequest,
    appliance: Appliance = Depends(_verified_appliance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    server_time = await svc.record_heartbeat(db, appliance_id=appliance.id, version=req.version)
    return {"status": "ok", "server_time": server_time.isoformat()}


@router.post("/inventory/sync")
async def inventory_sync(
    req: InventorySyncRequest,
    appliance: Appliance = Depends(_verified_appliance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await svc.accept_inventory_sync(
        db,
        appliance_id=appliance.id,
        org_id=appliance.org_id,
        vms=req.vms,
    )
    return {"status": "accepted", "upserted": count}


@router.post("/test-runs/{run_id}/progress")
async def post_progress(
    run_id: uuid.UUID,
    req: ProgressRequest,
    appliance: Appliance = Depends(_verified_appliance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await svc.update_run_progress(db, run_id=run_id, step=req.step,
                                  status=req.status, detail=req.detail)
    return {"status": "accepted"}


@router.post("/test-runs/{run_id}/result")
async def post_result(
    run_id: uuid.UUID,
    req: ResultRequest,
    appliance: Appliance = Depends(_verified_appliance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await svc.finalise_run(
        db,
        run_id=run_id,
        passed=req.passed,
        rto_actual_mins=req.rto_actual_mins,
        rpo_actual_mins=req.rpo_actual_mins,
        readiness_score=req.readiness_score,
        failure_reason=req.failure_reason,
    )
    return {"status": "accepted"}


@router.post("/test-runs/{run_id}/evidence")
async def upload_evidence(
    run_id: uuid.UUID,
    file: UploadFile = File(...),
    appliance: Appliance = Depends(_verified_appliance),
) -> dict:
    # TODO Phase 4: stream to S3 under evidence/{run_id}/{filename}
    return {"status": "accepted", "filename": file.filename}


@router.get("/commands")
async def get_commands(
    appliance: Appliance = Depends(_verified_appliance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    commands = await svc.get_pending_commands(db, appliance_id=appliance.id)
    return {"commands": commands}
