"""Stripe billing integration and plan management."""
from __future__ import annotations
import os
from typing import Any

PLANS = {
    "starter": {
        "name": "Starter",
        "workload_limit": 10,
        "price_per_workload_cents": 0,
        "base_price_cents": 49900,
        # $499/month flat
        "features": ["10 workloads", "All providers", "SOC 2 / ISO 27001 reports", "Email support"],
        "stripe_price_id": os.getenv("STRIPE_PRICE_STARTER", ""),
    },
    "growth": {
        "name": "Growth",
        "workload_limit": 50,
        "price_per_workload_cents": 0,
        "base_price_cents": 149900,
        # $1,499/month flat
        "features": ["50 workloads", "All providers", "All compliance frameworks", "RBAC + SSO", "API keys", "Integrations", "Priority support"],
        "stripe_price_id": os.getenv("STRIPE_PRICE_GROWTH", ""),
    },
    "enterprise": {
        "name": "Enterprise",
        "workload_limit": 999999,
        "price_per_workload_cents": 2500,
        # $25/workload/month
        "base_price_cents": 0,
        "features": ["Unlimited workloads", "All features", "MSSP console", "Custom SLA", "Dedicated CSM", "On-prem deployment option"],
        "stripe_price_id": os.getenv("STRIPE_PRICE_ENTERPRISE", ""),
    },
}


def get_plan(plan_name: str) -> dict[str, Any]:
    return PLANS.get(plan_name, PLANS["starter"])


def is_within_limit(subscription: Any, current_workload_count: int) -> bool:
    plan = get_plan(subscription.plan)
    return current_workload_count <= plan["workload_limit"]


async def create_stripe_customer(org_name: str, email: str) -> str | None:
    """Create a Stripe customer and return the customer ID."""
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        if not stripe.api_key:
            return None
        customer = stripe.Customer.create(name=org_name, email=email)
        return customer["id"]
    except Exception:
        return None


async def create_checkout_session(
    customer_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str | None:
    """Create a Stripe Checkout session and return the URL."""
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        price_id = PLANS.get(plan, {}).get("stripe_price_id", "")
        if not price_id:
            return None
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session["url"]
    except Exception:
        return None


async def cancel_subscription(stripe_subscription_id: str) -> bool:
    """Cancel a Stripe subscription at period end."""
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=True)
        return True
    except Exception:
        return False


def compute_monthly_bill(plan: str, workload_count: int) -> int:
    """Return estimated monthly bill in cents."""
    p = PLANS.get(plan, PLANS["starter"])
    base = p["base_price_cents"]
    per_unit = p["price_per_workload_cents"] * workload_count
    return base + per_unit
