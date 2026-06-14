from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db

router = APIRouter()


class TriggerTestRunRequest(BaseModel):
    workload_id: uuid.UUID
    restore_point: str | None = None   # ISO timestamp; None = latest


class TestRunResponse(BaseModel):
    id: uuid.UUID
    workload_id: uuid.UUID
    status: str
    started_at: str | None
    completed_at: str | None
    rto_actual_mins: int | None
    rpo_actual_mins: int | None
    readiness_score: int | None
    steps: list[dict] = []

    model_config = {"from_attributes": True}


@router.post("", response_model=TestRunResponse)
async def trigger_test_run(
    req: TriggerTestRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Creates a TestRun record and enqueues a Temporal workflow
    run_id = uuid.uuid4()
    return {
        "id": run_id,
        "workload_id": req.workload_id,
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "rto_actual_mins": None,
        "rpo_actual_mins": None,
        "readiness_score": None,
    }


@router.get("/{run_id}", response_model=TestRunResponse)
async def get_test_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    return {}


@router.get("/{run_id}/report")
async def download_report(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    # Returns presigned S3 URL to the PDF report
    return {"url": ""}
