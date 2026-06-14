from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db

router = APIRouter()


@router.get("/readiness")
async def org_readiness(db: AsyncSession = Depends(get_db)) -> dict:
    """Org-level readiness score: weighted average across all workloads."""
    return {
        "overall_score": 0,
        "workloads_tested": 0,
        "workloads_total": 0,
        "rto_compliance_pct": 0,
        "rpo_compliance_pct": 0,
        "trend": [],
    }


@router.get("/coverage")
async def coverage(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Percentage of workloads tested at least once in the last N days."""
    return {"tested_pct": 0, "untested_workloads": []}
