"""Unit tests for MSSP billing computation."""
from src.services.mssp_billing import (
    DEFAULT_TIER,
    compute_line_item,
    rate_for_tier,
    summarize_billing,
)


def test_rate_for_unknown_tier_falls_back_to_standard():
    assert rate_for_tier("gold") == rate_for_tier(DEFAULT_TIER)


def test_compute_line_item_standard():
    li = compute_line_item("Acme", "standard", workloads=10, test_runs=20)
    # base 0 + 10*5.00 + 20*0.50 = 60.00
    assert li["workload_cost"] == 50.0
    assert li["test_run_cost"] == 10.0
    assert li["total"] == 60.0


def test_compute_line_item_premium():
    li = compute_line_item("Globex", "premium", workloads=5, test_runs=4)
    # base 200 + 5*8.00 + 4*0.75 = 243.00
    assert li["total"] == 243.0
    assert li["base_fee"] == 200.0


def test_unknown_tier_normalized_and_priced_as_standard():
    li = compute_line_item("Initech", "gold", workloads=2, test_runs=0)
    assert li["tier"] == "standard"
    assert li["total"] == 10.0  # 2 * 5.00


def test_summarize_billing_rolls_up():
    items = [
        compute_line_item("A", "standard", 10, 20),   # 60.00
        compute_line_item("B", "premium", 5, 4),       # 243.00
    ]
    summary = summarize_billing(items)
    assert summary["customer_count"] == 2
    assert summary["total_workloads"] == 15
    assert summary["total_test_runs"] == 24
    assert summary["total_due"] == 303.0
    assert summary["currency"] == "USD"
