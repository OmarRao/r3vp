"""
Multi-cloud readiness and provider breakdown endpoints.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser, CurrentUser
from src.db.session import get_db
from src.models.workload import Workload
from src.models.test_run import TestRun

router = APIRouter(prefix="/v1/multicloud", tags=["multicloud"])

PROVIDERS = [
    "vmware",
    "hyperv",
    "azure",
    "aws",
    "proxmox",
    "nutanix",
    "rhv",
    "xenserver",
    "sangfor",
    "gcp",
]


@router.get("/provider-summary")
async def provider_summary(
    user: CurrentUser = Depends(AuthUser),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Return a readiness breakdown by provider.

    For each provider that has at least one workload, returns:
    - workload count
    - tested count (at least one completed test run)
    - pass rate (% of completed runs that passed)
    - average actual RTO (minutes)
    """
    from sqlalchemy import case

    rows = (await db.execute(
        select(
            Workload.provider,
            func.count(Workload.id.distinct()).label("total"),
        )
        .join(
            # Left join to appliances to scope by org
            __import__("src.models.appliance", fromlist=["Appliance"]).Appliance,
            Workload.appliance_id == __import__("src.models.appliance", fromlist=["Appliance"]).Appliance.id,
        )
        .where(
            __import__("src.models.appliance", fromlist=["Appliance"]).Appliance.org_id == user.org_id
        )
        .group_by(Workload.provider)
    )).all()

    result = []
    for row in rows:
        provider = row.provider or "vmware"
        total = row.total

        # Fetch run stats for this provider
        run_stats = (await db.execute(
            select(
                func.count(TestRun.id).label("total_runs"),
                func.sum(case((TestRun.status == "passed", 1), else_=0)).label("passed_runs"),
                func.avg(TestRun.rto_actual_mins).label("avg_rto"),
            )
            .join(Workload, TestRun.workload_id == Workload.id)
            .join(
                __import__("src.models.appliance", fromlist=["Appliance"]).Appliance,
                Workload.appliance_id == __import__("src.models.appliance", fromlist=["Appliance"]).Appliance.id,
            )
            .where(
                __import__("src.models.appliance", fromlist=["Appliance"]).Appliance.org_id == user.org_id,
                Workload.provider == provider,
                TestRun.status.in_(["passed", "failed"]),
            )
        )).one()

        total_runs = run_stats.total_runs or 0
        passed_runs = run_stats.passed_runs or 0
        avg_rto = float(run_stats.avg_rto) if run_stats.avg_rto else None
        pass_rate = round((passed_runs / total_runs) * 100) if total_runs > 0 else None

        result.append({
            "provider": provider,
            "total_workloads": total,
            "total_runs": total_runs,
            "pass_rate": pass_rate,
            "avg_rto_mins": round(avg_rto, 1) if avg_rto else None,
        })

    # Ensure all providers appear even if they have no workloads yet
    present = {r["provider"] for r in result}
    for p in PROVIDERS:
        if p not in present:
            result.append({
                "provider": p,
                "total_workloads": 0,
                "total_runs": 0,
                "pass_rate": None,
                "avg_rto_mins": None,
            })

    # Sort by workload count descending
    result.sort(key=lambda r: r["total_workloads"], reverse=True)
    return result


@router.get("/workloads")
async def list_workloads_by_provider(
    provider: str | None = None,
    user: CurrentUser = Depends(AuthUser),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List workloads with optional provider filter."""
    from src.models.appliance import Appliance

    q = (
        select(Workload)
        .join(Appliance, Workload.appliance_id == Appliance.id)
        .where(Appliance.org_id == user.org_id)
    )
    if provider:
        q = q.where(Workload.provider == provider)
    q = q.order_by(Workload.name)

    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(w.id),
            "name": w.name,
            "provider": w.provider or "vmware",
            "platform": w.platform,
            "os_type": w.os_type,
            "is_protected": w.is_protected,
            "cloud_resource_id": w.cloud_resource_id,
            "cloud_region": w.cloud_region,
            "rto_target_mins": w.rto_target_mins,
            "rpo_target_mins": w.rpo_target_mins,
            "last_test_run_status": w.last_test_run_status,
            "last_backup_at": w.last_backup_at.isoformat() if w.last_backup_at else None,
        }
        for w in rows
    ]
