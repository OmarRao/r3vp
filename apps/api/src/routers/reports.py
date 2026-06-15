"""Reporting endpoints: cyber insurance PDF and summary data."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db

router = APIRouter()


@router.get("/cyber-insurance")
async def cyber_insurance_report(
    user: AuthUser,
    from_date: str = Query(..., description="Start date YYYY-MM-DD"),
    to_date: str = Query(..., description="End date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    from fastapi.responses import Response
    from datetime import datetime, timezone
    from jinja2 import Environment, FileSystemLoader
    import weasyprint
    import os

    try:
        from_dt = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
        to_dt = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    from src.models.test_run import TestRun
    from src.models.workload import Workload
    from src.models.appliance import Appliance, Org

    # Fetch org name
    org = await db.scalar(select(Org).where(Org.id == user.org_id))
    org_name = org.name if org else str(user.org_id)

    # Fetch all test runs in period for this org
    rows = await db.execute(
        select(TestRun, Workload)
        .join(Workload, TestRun.workload_id == Workload.id)
        .join(Appliance, Workload.appliance_id == Appliance.id)
        .where(
            Appliance.org_id == user.org_id,
            TestRun.completed_at >= from_dt,
            TestRun.completed_at <= to_dt,
        )
        .order_by(TestRun.completed_at.desc())
    )
    results = rows.all()

    workload_results = []
    total_runs = len(results)
    passed_runs = 0
    rto_compliant = 0
    rpo_compliant = 0
    rto_sum = 0
    rto_count = 0

    for run, wl in results:
        passed = run.status == "passed"
        if passed:
            passed_runs += 1

        rto_ok = (run.rto_actual_mins or 0) <= (wl.rto_target_mins or 9999) if wl.rto_target_mins else True
        rpo_ok = (run.rpo_actual_mins or 0) <= (wl.rpo_target_mins or 9999) if wl.rpo_target_mins else True

        if rto_ok:
            rto_compliant += 1
        if rpo_ok:
            rpo_compliant += 1
        if run.rto_actual_mins:
            rto_sum += run.rto_actual_mins
            rto_count += 1

        workload_results.append({
            "workload_name": wl.name,
            "test_date": run.completed_at.strftime("%Y-%m-%d %H:%M") if run.completed_at else "",
            "rto_target": wl.rto_target_mins,
            "rto_actual": run.rto_actual_mins,
            "rto_ok": rto_ok,
            "rpo_target": wl.rpo_target_mins,
            "rpo_actual": run.rpo_actual_mins,
            "rpo_ok": rpo_ok,
            "readiness_score": run.readiness_score,
            "passed": passed,
        })

    pass_rate_pct = round(passed_runs / total_runs * 100) if total_runs else 0
    rto_compliance_pct = round(rto_compliant / total_runs * 100) if total_runs else 0
    rpo_compliance_pct = round(rpo_compliant / total_runs * 100) if total_runs else 0
    avg_rto_mins = round(rto_sum / rto_count) if rto_count else 0

    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(os.path.abspath(templates_dir)))
    template = env.get_template("cyber_insurance_report.html")

    html = template.render(
        org_name=org_name,
        from_date=from_date,
        to_date=to_date,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        total_tested=len(set(r[1].id for r in results)),
        total_runs=total_runs,
        pass_rate_pct=pass_rate_pct,
        rto_compliance_pct=rto_compliance_pct,
        rpo_compliance_pct=rpo_compliance_pct,
        avg_rto_mins=avg_rto_mins,
        workload_results=workload_results,
    )

    pdf_bytes = weasyprint.HTML(string=html).write_pdf()
    filename = f"r3vp-cyber-insurance-{from_date}-{to_date}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
