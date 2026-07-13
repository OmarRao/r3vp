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
    from sqlalchemy import func, select

    from src.models.appliance import Appliance
    from src.models.test_run import TestRun
    from src.models.workload import Workload
    from src.services.readiness_scoring import days_since, fail_rate_pct

    require_permission(getattr(user, "permissions", []), "workloads:read")

    # Per-workload run aggregates for this org.
    agg = (await db.execute(
        select(
            Workload.id,
            Workload.name,
            Workload.provider,
            Workload.rto_target_mins,
            func.count(TestRun.id).label("runs"),
            func.count(TestRun.id).filter(TestRun.status == "failed").label("fails"),
            func.max(TestRun.started_at).label("last_test"),
        )
        .select_from(Workload).join(Appliance)
        .outerjoin(TestRun, TestRun.workload_id == Workload.id)
        .where(Appliance.org_id == user.org_id)
        .group_by(Workload.id, Workload.name, Workload.provider, Workload.rto_target_mins)
    )).all()

    # Latest recorded RTO per workload (Postgres DISTINCT ON the workload).
    latest = (await db.execute(
        select(TestRun.workload_id, TestRun.rto_actual_mins)
        .join(Workload).join(Appliance)
        .where(Appliance.org_id == user.org_id, TestRun.rto_actual_mins.isnot(None))
        .order_by(TestRun.workload_id, TestRun.started_at.desc())
        .distinct(TestRun.workload_id)
    )).all()
    latest_rto = {wid: rto for wid, rto in latest}

    inputs = [
        {
            "name": r.name,
            "provider": r.provider or "vmware",
            # Never-tested workloads are treated as maximally stale.
            "days_since_test": days_since(r.last_test) if r.last_test else 999,
            "rto_actual_mins": latest_rto.get(r.id, 0),
            "rto_target_mins": r.rto_target_mins or 999,
            "fail_rate_pct": fail_rate_pct(r.runs, r.fails),
        }
        for r in agg
    ]
    ranked = rank_workload_risks(inputs)
    return {"workloads": ranked, "high_risk_count": sum(1 for w in ranked if w["risk_level"] == "high")}


@router.post("/query")
async def natural_language_query(body: dict, user: AuthUser, db: AsyncSession = Depends(get_db)):
    from src.services.insights_context import build_query_context

    require_permission(getattr(user, "permissions", []), "workloads:read")
    query = body.get("query", "")
    if not query or len(query) > 500:
        from fastapi import HTTPException
        raise HTTPException(400, "query must be 1-500 characters")
    context = await build_query_context(db, user.org_id)
    answer = answer_nl_query(query, context)
    return {"query": query, "answer": answer}
