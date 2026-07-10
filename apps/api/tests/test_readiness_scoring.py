"""Unit tests for the recovery-readiness scoring helpers (pure, no DB)."""
from datetime import UTC, datetime, timedelta

from src.services.readiness_scoring import (
    bucket_weekly_pass_rate,
    compute_composite_score,
    days_since,
    fail_rate_pct,
)


def test_composite_score_bounds_and_monotonicity():
    # Perfect posture scores at or near 100; empty posture scores 0.
    perfect = compute_composite_score(10, 10, 10, 100, active_threats=0, open_incidents=0)
    empty = compute_composite_score(0, 0, 0, 0)
    assert 0 <= empty <= perfect <= 100
    assert empty == 0
    assert perfect >= 90


def test_composite_score_threats_penalize():
    base = compute_composite_score(10, 10, 10, 100, active_threats=0, open_incidents=0)
    penalized = compute_composite_score(10, 10, 10, 100, active_threats=5, open_incidents=3)
    assert penalized < base


def test_weekly_trend_buckets_and_gaps():
    now = datetime(2026, 7, 1, tzinfo=UTC)
    # Two runs in the most recent week: one pass, one fail -> 50%.
    runs = [
        (now - timedelta(days=1), True),
        (now - timedelta(days=2), False),
        # One run three weeks ago: pass -> 100%.
        (now - timedelta(weeks=3, days=1), True),
    ]
    trend = bucket_weekly_pass_rate(runs, weeks=12, now=now)
    assert len(trend) == 12
    assert trend[-1]["runs"] == 2
    assert trend[-1]["pass_rate"] == 50
    # A week with no runs reports None, not 0.
    empty_weeks = [b for b in trend if b["runs"] == 0]
    assert all(b["pass_rate"] is None for b in empty_weeks)


def test_days_since():
    now = datetime(2026, 7, 1, tzinfo=UTC)
    assert days_since(None) is None
    assert days_since(now - timedelta(days=10), now=now) == 10
    # Future timestamps clamp to 0 rather than going negative.
    assert days_since(now + timedelta(days=5), now=now) == 0


def test_fail_rate_pct():
    assert fail_rate_pct(0, 0) == 0
    assert fail_rate_pct(4, 1) == 25
    assert fail_rate_pct(3, 1) == 33
    assert fail_rate_pct(2, 2) == 100
