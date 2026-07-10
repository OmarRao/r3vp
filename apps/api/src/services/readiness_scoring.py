"""Recovery-readiness scoring helpers.

Turns raw test-run aggregates into the composite readiness score and a rolling
weekly trend. The composite formula lives in ``executive_report.compute_scorecard``
(coverage 40%, pass rate 35%, RTO compliance 15%, threat/incident penalty) and is
reused here so the dashboard, scorecard, and executive report all agree.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from src.services.executive_report import compute_scorecard


def compute_composite_score(
    workloads_total: int,
    workloads_tested: int,
    workloads_passing: int,
    rto_compliance_pct: int,
    active_threats: int = 0,
    open_incidents: int = 0,
) -> int:
    """Composite recovery-readiness score (0-100). Thin, named wrapper around
    the shared scorecard formula so callers do not depend on the report module
    directly."""
    return compute_scorecard(
        workloads_total=workloads_total,
        workloads_tested=workloads_tested,
        workloads_passing=workloads_passing,
        rto_compliance_pct=rto_compliance_pct,
        active_threats=active_threats,
        open_incidents=open_incidents,
    )


def bucket_weekly_pass_rate(
    runs: list[tuple[datetime, bool]],
    weeks: int = 12,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Bucket completed runs into the last ``weeks`` weekly windows.

    ``runs`` is a list of ``(completed_at, passed)`` tuples. Returns one entry
    per week (oldest first) with the pass rate and run count. Weeks with no runs
    report ``pass_rate=None`` so the caller can render a gap rather than a zero.
    """
    now = now or datetime.now(UTC)
    buckets: list[dict[str, Any]] = []
    for w in range(weeks - 1, -1, -1):
        end = now - timedelta(weeks=w)
        start = end - timedelta(weeks=1)
        window = [passed for (ts, passed) in runs if start < ts <= end]
        total = len(window)
        passed_n = sum(1 for p in window if p)
        buckets.append(
            {
                "week_ending": end.date().isoformat(),
                "runs": total,
                "pass_rate": round(passed_n / total * 100) if total else None,
            }
        )
    return buckets


def days_since(ts: datetime | None, now: datetime | None = None) -> int | None:
    """Whole days between ``ts`` and now, or None if ``ts`` is missing."""
    if ts is None:
        return None
    now = now or datetime.now(UTC)
    return max(0, (now - ts).days)


def fail_rate_pct(total_runs: int, failed_runs: int) -> int:
    """Failure rate as a whole percentage; 0 when there are no runs."""
    if not total_runs:
        return 0
    return round(failed_runs / total_runs * 100)
