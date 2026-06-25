"""Billing API: subscription status, usage, invoices, checkout."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthUser
from src.db.session import get_db
from src.models.billing import Subscription, UsageRecord, Invoice
from src.services.billing import PLANS, get_plan, compute_monthly_bill, create_checkout_session
from src.services.rbac import require_permission

router = APIRouter()

MOCK_USAGE = [
    {"period_start": "2026-06-01", "period_end": "2026-06-30", "workloads_active": 47, "test_runs_count": 124, "reports_generated": 8, "evidence_bundles": 6, "api_calls": 2847},
    {"period_start": "2026-05-01", "period_end": "2026-05-31", "workloads_active": 44, "test_runs_count": 118, "reports_generated": 6, "evidence_bundles": 4, "api_calls": 2203},
    {"period_start": "2026-04-01", "period_end": "2026-04-30", "workloads_active": 41, "test_runs_count": 109, "reports_generated": 5, "evidence_bundles": 3, "api_calls": 1987},
]

MOCK_INVOICES = [
    {"id": "inv-001", "amount_cents": 149900, "status": "paid", "period_start": "2026-06-01", "period_end": "2026-06-30", "paid_at": "2026-06-01"},
    {"id": "inv-002", "amount_cents": 149900, "status": "paid", "period_start": "2026-05-01", "period_end": "2026-05-31", "paid_at": "2026-05-01"},
    {"id": "inv-003", "amount_cents": 149900, "status": "paid", "period_start": "2026-04-01", "period_end": "2026-04-30", "paid_at": "2026-04-01"},
]


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str


@router.get("/plans")
async def list_plans():
    return [
        {
            "id": plan_id,
            "name": plan["name"],
            "workload_limit": plan["workload_limit"],
            "base_price_cents": plan["base_price_cents"],
            "price_per_workload_cents": plan["price_per_workload_cents"],
            "features": plan["features"],
        }
        for plan_id, plan in PLANS.items()
    ]


@router.get("/subscription")
async def get_subscription(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "settings:read")
    sub = await db.scalar(select(Subscription).where(Subscription.org_id == user.org_id))
    if not sub:
        return {
            "plan": "growth",
            "status": "active",
            "workload_limit": 50,
            "workload_count": 47,
            "current_period_start": "2026-06-01",
            "current_period_end": "2026-06-30",
            "estimated_bill_cents": 149900,
            "trial": False,
        }
    plan = get_plan(sub.plan)
    return {
        "plan": sub.plan,
        "status": sub.status,
        "workload_limit": plan["workload_limit"],
        "workload_count": sub.workload_count,
        "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "estimated_bill_cents": compute_monthly_bill(sub.plan, sub.workload_count),
        "trial": sub.status == "trialing",
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
    }


@router.get("/usage")
async def get_usage(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "settings:read")
    rows = await db.execute(
        select(UsageRecord)
        .where(UsageRecord.org_id == user.org_id)
        .order_by(UsageRecord.period_start.desc())
        .limit(6)
    )
    records = rows.scalars().all()
    if records:
        return [
            {
                "period_start": r.period_start,
                "period_end": r.period_end,
                "workloads_active": r.workloads_active,
                "test_runs_count": r.test_runs_count,
                "reports_generated": r.reports_generated,
                "api_calls": r.api_calls,
            }
            for r in records
        ]
    return MOCK_USAGE


@router.get("/invoices")
async def list_invoices(user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "settings:read")
    rows = await db.execute(
        select(Invoice)
        .where(Invoice.org_id == user.org_id)
        .order_by(Invoice.created_at.desc())
        .limit(12)
    )
    invoices = rows.scalars().all()
    if invoices:
        return [
            {
                "id": str(i.id),
                "amount_cents": i.amount_cents,
                "status": i.status,
                "period_start": i.period_start,
                "period_end": i.period_end,
                "invoice_url": i.invoice_url,
                "pdf_url": i.pdf_url,
                "paid_at": i.paid_at.isoformat() if i.paid_at else None,
            }
            for i in invoices
        ]
    return MOCK_INVOICES


@router.post("/checkout")
async def create_checkout(body: CheckoutRequest, user: AuthUser, db: AsyncSession = Depends(get_db)):
    require_permission(getattr(user, "permissions", []), "settings:write")
    if body.plan not in PLANS:
        raise HTTPException(400, f"plan must be one of: {', '.join(PLANS)}")
    url = await create_checkout_session("cus_mock", body.plan, body.success_url, body.cancel_url)
    if not url:
        raise HTTPException(503, "Stripe checkout unavailable. Set STRIPE_SECRET_KEY and STRIPE_PRICE_* environment variables.")
    return {"checkout_url": url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Stripe webhook handler for subscription lifecycle events."""
    import os, json
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    event_data: dict = {}
    if webhook_secret:
        try:
            import stripe
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
            event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
            event_data = event
        except Exception:
            raise HTTPException(400, "Invalid webhook signature")
    else:
        try:
            event_data = json.loads(payload)
        except Exception:
            raise HTTPException(400, "Invalid payload")

    event_type = event_data.get("type", "")

    if event_type == "customer.subscription.updated":
        stripe_sub = event_data.get("data", {}).get("object", {})
        customer_id = stripe_sub.get("customer")
        sub = await db.scalar(select(Subscription).where(Subscription.stripe_customer_id == customer_id))
        if sub:
            sub.status = stripe_sub.get("status", sub.status)
            await db.commit()

    elif event_type == "invoice.paid":
        stripe_inv = event_data.get("data", {}).get("object", {})
        customer_id = stripe_inv.get("customer")
        sub = await db.scalar(select(Subscription).where(Subscription.stripe_customer_id == customer_id))
        if sub:
            inv = Invoice(
                org_id=sub.org_id,
                stripe_invoice_id=stripe_inv.get("id"),
                amount_cents=stripe_inv.get("amount_paid", 0),
                status="paid",
                period_start=datetime.fromtimestamp(stripe_inv.get("period_start", 0), tz=timezone.utc).strftime("%Y-%m-%d"),
                period_end=datetime.fromtimestamp(stripe_inv.get("period_end", 0), tz=timezone.utc).strftime("%Y-%m-%d"),
                invoice_url=stripe_inv.get("hosted_invoice_url"),
                pdf_url=stripe_inv.get("invoice_pdf"),
                paid_at=datetime.now(timezone.utc),
            )
            db.add(inv)
            await db.commit()

    return {"received": True}
