"""AI Insights endpoints: predictions, anomalies, risk ranking, NL queries."""
# Author: Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.services.ai_insights import (
    answer_nl_query,
    detect_anomalies,
    predict_rto_trend,
    rank_workload_risks,
)
from src.services.rbac import require_permission

router = APIRouter()

MOCK_WORKLOADS = [
    {"name": "db-prod-03", "provider": "vmware", "days_since_test": 3, "rto_actual_mins": 52, "rto_target_mins": 60, "fail_rate_pct": 33},
    {"name": "auth-svc-01", "provider": "azure", "days_since_test": 45, "rto_actual_mins": 18, "rto_target_mins": 30, "fail_rate_pct": 0},
    {"name": "erp-prod-01", "provider": "vmware", "days_since_test": 7, "rto_actual_mins": 88, "rto_target_mins": 120, "fail_rate_pct": 33},
    {"name": "dc-01.prod", "provider": "hyperv", "days_since_test": 1, "rto_actual_mins": 12, "rto_target_mins": 60, "fail_rate_pct": 0},
    {"name": "sql-prod-02", "provider": "aws", "days_since_test": 5, "rto_actual_mins": 95, "rto_target_mins": 90, "fail_rate_pct": 50},
]

MOCK_CONTEXT = {
    "workloads_total": 47,
    "workloads_tested": 44,
    "overall_score": 84,
    "active_threats": 1,
    "rto_breaches": [
        {"workload": "sql-prod-02", "rto_actual": 95, "rto_target": 90},
    ],
    "recent_failures": [
        {"workload": "sql-prod-02"},
        {"workload": "db-prod-03"},
    ],
    "provider_breakdown": {
        "vmware": {"pass_rate": 95},
        "azure": {"pass_rate": 80},
        "aws": {"pass_rate": 75},
        "gcp": {"pass_rate": 75},
        "hyperv": {"pass_rate": 100},
    },
}


@router.get("/rto-prediction/{workload_id}")
async def get_rto_prediction(workload_id: str, user: AuthUser, db: AsyncSession = Depends(get_db)):
    import uuid

    from fastapi import HTTPException
    from sqlalchemy import select

    from src.models.appliance import Appliance
    from src.models.test_run import TestRun
    from src.models.workload import Workload

    require_permission(getattr(user, "permissions", []), "workloads:read")

    try:
        wid = uuid.UUID(workload_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid workload id") from exc

    # Scope to the caller's org so one tenant cannot read another's workload.
    workload = await db.scalar(
        select(Workload).join(Appliance).where(
            Workload.id == wid, Appliance.org_id == user.org_id
        )
    )
    if workload is None:
        raise HTTPException(404, "Workload not found")

    rows = (await db.execute(
        select(TestRun.rto_actual_mins)
        .where(
            TestRun.workload_id == wid,
            TestRun.status == "passed",
            TestRun.rto_actual_mins.isnot(None),
        )
        .order_by(TestRun.started_at)
    )).scalars().all()
    rto_series = [float(r) for r in rows]

    target = float(workload.rto_target_mins or 60)
    prediction = predict_rto_trend(rto_series, target_mins=target)
    anomalies = detect_anomalies(rto_series)
    return {"workload_id": workload_id, "rto_series": rto_series, "prediction": prediction, "anomalies": anomalies}


@router.get("/risk-ranking")
async def get_risk_ranking(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:read")
    ranked = rank_workload_risks(MOCK_WORKLOADS)
    return {"workloads": ranked, "high_risk_count": sum(1 for w in ranked if w["risk_level"] == "high")}


@router.post("/query")
async def natural_language_query(body: dict, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "workloads:read")
    query = body.get("query", "")
    if not query or len(query) > 500:
        from fastapi import HTTPException
        raise HTTPException(400, "query must be 1-500 characters")
    answer = answer_nl_query(query, MOCK_CONTEXT)
    return {"query": query, "answer": answer}
