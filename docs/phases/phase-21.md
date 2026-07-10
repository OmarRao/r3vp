# Phase 21: Recovery Intelligence (Real Readiness Scoring + RTO Forecasting)

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 21 turns the previously mocked recovery-intelligence surfaces into real,
server-computed metrics driven by test-run history. The AI insight functions
(linear-regression RTO prediction, z-score anomaly detection, composite risk
scoring) already existed as pure functions; this phase wires them to live data
and makes the dashboard readiness score a true composite with a rolling trend.

---

## Readiness Scoring

`src/services/readiness_scoring.py` adds:

- `compute_composite_score(...)`: a named wrapper over the shared scorecard
  formula (`executive_report.compute_scorecard`) so the dashboard, scorecard, and
  executive report all agree. Weighting: coverage 40%, pass rate 35%, RTO
  compliance 15%, threat/incident penalty.
- `bucket_weekly_pass_rate(runs, weeks=12)`: buckets completed runs into weekly
  windows, reporting pass rate and run count per week, with `None` (a gap) for
  weeks that had no runs.
- `days_since(ts)`: whole days since a timestamp, clamped at 0.

All three are pure and unit-tested.

## Endpoint Changes

`GET /v1/dashboard/readiness`:
- Returns a real composite `overall_score` (was a naive average of the
  `readiness_score` column).
- Populates the previously empty `trend` with a rolling 12-week pass-rate series.
- Uses distinct workload counts. The prior query counted workloads across the
  run-joined result set, inflating `workloads_total` and `workloads_tested` by
  the number of test runs.
- Adds `workloads_passing` (distinct workloads with at least one passed run).

`GET /v1/insights/rto-prediction/{workload_id}`:
- Runs the RTO forecast and anomaly detection over the workload's real recorded
  RTO history (ordered passed runs), using the workload's actual RTO target,
  instead of a fixed mock series.
- Verifies the workload belongs to the caller's org (previously unscoped, a
  cross-tenant read); returns 404 otherwise and 400 on a malformed id.

## Testing

- Unit tests (`tests/test_readiness_scoring.py`): composite-score bounds and
  monotonicity, threat penalty, weekly-trend bucketing and gaps, `days_since`.
- Integration test (`tests/integration/test_readiness_endpoint.py`): seeds an org,
  two workloads, and passed/failed runs, calls `/v1/dashboard/readiness` with the
  DB and auth dependencies overridden, and asserts the distinct counts, a
  computed score, and the 12-week trend. Verified locally against Postgres 16 and
  in the CI integration job.

## Risk Ranking (now real)

`/v1/insights/risk-ranking` ranks workloads from real per-workload aggregates:
latest recorded RTO (Postgres `DISTINCT ON`), failure rate, and days since last
test, all org-scoped, fed into the existing `rank_workload_risks` scorer.

Wiring this up surfaced a real RBAC bug: every `require_permission`-gated
endpoint returned 403 for authenticated users because `CurrentUser` had no
`permissions` attribute (so `getattr(user, "permissions", [])` was always empty).
`CurrentUser.permissions` is now derived from the role via the RBAC system-role
map. The whole AI Insights router was effectively inaccessible before this.

## Still Mocked (follow-up)

`/v1/insights/query` (natural-language) still answers from mock context; wiring
it to a live aggregate context is the remaining increment.

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
