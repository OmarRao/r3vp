"""MSSP usage metering and billing computation.

Turns per-customer usage (protected workloads + recovery test runs in the billing
period) into a priced line item using a per-tier rate card, and rolls the line
items into a portfolio summary. Pure and side-effect free so it is unit-testable;
the router supplies the real usage counts from the database.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/
"""
from __future__ import annotations

from typing import Any

# Monthly rate card by customer tier (USD): a base platform fee plus metered
# per-workload protection and per-recovery-test charges.
RATE_CARD: dict[str, dict[str, float]] = {
    "standard": {"base": 0.0, "per_workload": 5.0, "per_test_run": 0.50},
    "premium": {"base": 200.0, "per_workload": 8.0, "per_test_run": 0.75},
    "enterprise": {"base": 500.0, "per_workload": 12.0, "per_test_run": 1.00},
}
DEFAULT_TIER = "standard"


def rate_for_tier(tier: str) -> dict[str, float]:
    """Return the rate card for a tier, falling back to the standard tier."""
    return RATE_CARD.get(tier, RATE_CARD[DEFAULT_TIER])


def compute_line_item(display_name: str, tier: str, workloads: int, test_runs: int) -> dict[str, Any]:
    """Price one customer's usage for the billing period."""
    rate = rate_for_tier(tier)
    workload_cost = round(workloads * rate["per_workload"], 2)
    test_run_cost = round(test_runs * rate["per_test_run"], 2)
    total = round(rate["base"] + workload_cost + test_run_cost, 2)
    return {
        "customer": display_name,
        "tier": tier if tier in RATE_CARD else DEFAULT_TIER,
        "workloads": workloads,
        "test_runs": test_runs,
        "base_fee": rate["base"],
        "workload_cost": workload_cost,
        "test_run_cost": test_run_cost,
        "total": total,
    }


def summarize_billing(line_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll priced line items into a portfolio-level summary."""
    return {
        "customer_count": len(line_items),
        "total_workloads": sum(li["workloads"] for li in line_items),
        "total_test_runs": sum(li["test_runs"] for li in line_items),
        "total_due": round(sum(li["total"] for li in line_items), 2),
        "currency": "USD",
    }
