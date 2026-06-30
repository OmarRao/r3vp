"""MSSP console API: partner management, customer org rollup, cross-org insights."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.mssp import MsspAlertRule, MsspCustomerOrg
from src.services.rbac import require_permission

router = APIRouter()

MOCK_CUSTOMERS = [
    {"id": "c1", "org_id": "o1", "display_name": "Acme Corporation", "industry": "Financial Services", "tier": "premium", "readiness_score": 87, "workloads": 42, "workloads_tested": 40, "last_test": "Today 14:22", "active_threats": 0, "open_incidents": 0, "appliances": 3, "status": "healthy"},
    {"id": "c2", "org_id": "o2", "display_name": "Globex Industries", "industry": "Manufacturing", "tier": "standard", "readiness_score": 61, "workloads": 28, "workloads_tested": 18, "last_test": "Jun 20", "active_threats": 1, "open_incidents": 1, "appliances": 2, "status": "warning"},
    {"id": "c3", "org_id": "o3", "display_name": "Initech Solutions", "industry": "Technology", "tier": "enterprise", "readiness_score": 94, "workloads": 67, "workloads_tested": 66, "last_test": "Today 09:15", "active_threats": 0, "open_incidents": 0, "appliances": 5, "status": "healthy"},
    {"id": "c4", "org_id": "o4", "display_name": "Umbrella Medical", "industry": "Healthcare", "tier": "premium", "readiness_score": 72, "workloads": 35, "workloads_tested": 26, "last_test": "Jun 22", "active_threats": 0, "open_incidents": 0, "appliances": 2, "status": "healthy"},
    {"id": "c5", "org_id": "o5", "display_name": "Stark Logistics", "industry": "Retail", "tier": "standard", "readiness_score": 38, "workloads": 19, "workloads_tested": 8, "last_test": "Jun 10", "active_threats": 2, "open_incidents": 1, "appliances": 1, "status": "critical"},
]


class AddCustomerRequest(BaseModel):
    org_id: uuid.UUID
    display_name: str
    industry: str | None = None
    tier: str = "standard"
    tags: list[str] = []
    notes: str | None = None


class CreateAlertRuleRequest(BaseModel):
    name: str
    condition: str
    threshold: int | None = None
    applies_to: str = "all"
    notification_channel: str = "email"
    notification_target: str | None = None


@router.get("/summary")
async def mssp_summary(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "mssp:read")
    total = len(MOCK_CUSTOMERS)
    healthy = sum(1 for c in MOCK_CUSTOMERS if c["status"] == "healthy")
    warning = sum(1 for c in MOCK_CUSTOMERS if c["status"] == "warning")
    critical = sum(1 for c in MOCK_CUSTOMERS if c["status"] == "critical")
    avg_score = round(sum(c["readiness_score"] for c in MOCK_CUSTOMERS) / total)
    total_workloads = sum(c["workloads"] for c in MOCK_CUSTOMERS)
    active_threats = sum(c["active_threats"] for c in MOCK_CUSTOMERS)
    open_incidents = sum(c["open_incidents"] for c in MOCK_CUSTOMERS)
    return {
        "total_customers": total,
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "avg_readiness_score": avg_score,
        "total_workloads": total_workloads,
        "total_active_threats": active_threats,
        "total_open_incidents": open_incidents,
    }


@router.get("/customers")
async def list_customers(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "mssp:read")
    rows = await db.execute(
        select(MsspCustomerOrg)
        .order_by(MsspCustomerOrg.display_name)
    )
    customers = rows.scalars().all()
    if customers:
        return [
            {"id": str(c.id), "org_id": str(c.org_id), "display_name": c.display_name, "industry": c.industry, "tier": c.tier, "tags": c.tags}
            for c in customers
        ]
    return MOCK_CUSTOMERS


@router.post("/customers", status_code=201)
async def add_customer(body: AddCustomerRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "mssp:manage")
    customer = MsspCustomerOrg(
        mssp_id=user.org_id,
        org_id=body.org_id,
        display_name=body.display_name,
        industry=body.industry,
        tier=body.tier,
        tags=body.tags,
        notes=body.notes,
        onboarded_at=datetime.now(UTC),
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return {"id": str(customer.id), "display_name": customer.display_name}


@router.delete("/customers/{customer_id}", status_code=204)
async def remove_customer(customer_id: uuid.UUID, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "mssp:manage")
    customer = await db.scalar(select(MsspCustomerOrg).where(MsspCustomerOrg.id == customer_id))
    if not customer:
        raise HTTPException(404, "Customer org not found")
    await db.delete(customer)
    await db.commit()


@router.get("/customers/{customer_id}/scorecard")
async def customer_scorecard(customer_id: str, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "mssp:read")
    customer = next((c for c in MOCK_CUSTOMERS if c["id"] == customer_id), None)
    if not customer:
        raise HTTPException(404, "Customer not found")
    return {
        **customer,
        "trend": [82, 84, 85, 83, 86, 87] if customer["status"] == "healthy" else [55, 58, 60, 59, 61, customer["readiness_score"]],
        "top_risks": [
            {"workload": "db-prod-01", "rto_target": 60, "last_rto": 74, "risk": "high"},
            {"workload": "dc-prod-02", "rto_target": 30, "last_rto": 28, "risk": "medium"},
        ],
    }


@router.get("/alert-rules")
async def list_alert_rules(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "mssp:read")
    rows = await db.execute(select(MsspAlertRule).order_by(MsspAlertRule.created_at.desc()))
    rules = rows.scalars().all()
    if rules:
        return [{"id": str(r.id), "name": r.name, "condition": r.condition, "threshold": r.threshold, "enabled": r.enabled} for r in rules]
    return [
        {"id": "r1", "name": "Critical score alert", "condition": "readiness_below", "threshold": 50, "applies_to": "all", "notification_channel": "email", "enabled": True},
        {"id": "r2", "name": "Active threat alert", "condition": "threat_detected", "threshold": None, "applies_to": "tier:premium", "notification_channel": "email", "enabled": True},
        {"id": "r3", "name": "Stale test alert", "condition": "no_test_in_days", "threshold": 14, "applies_to": "all", "notification_channel": "email", "enabled": False},
    ]


@router.post("/alert-rules", status_code=201)
async def create_alert_rule(body: CreateAlertRuleRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "mssp:manage")
    VALID_CONDITIONS = {"readiness_below", "rto_breach", "test_failure", "no_test_in_days", "threat_detected"}
    if body.condition not in VALID_CONDITIONS:
        raise HTTPException(400, f"condition must be one of: {', '.join(sorted(VALID_CONDITIONS))}")
    rule = MsspAlertRule(
        mssp_id=user.org_id,
        name=body.name,
        condition=body.condition,
        threshold=body.threshold,
        applies_to=body.applies_to,
        notification_channel=body.notification_channel,
        notification_target=body.notification_target,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": str(rule.id), "name": rule.name}
