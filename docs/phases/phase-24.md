# Phase 24: Continuous Validation Execution

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 18 introduced the continuous-validation data model (policies, micro-validation
runs, alerts) and API. Phase 24 makes it actually run: the scheduler now executes
enabled policies on their interval and produces real runs and alerts, so
"always-on micro-validation" is a working loop rather than a schema.

---

## What Changed

### Scheduler wiring
`load_schedules` now registers each enabled `ContinuousValidationPolicy` with an
APScheduler `IntervalTrigger(minutes=check_interval_mins)` (id `cv-policy-<id>`),
alongside the existing workload test-run and report-schedule jobs.

### Policy execution (`_run_validation_policy`)
On each interval the job:
1. Loads the policy (skips if disabled).
2. Resolves in-scope workloads (join to appliance for org scoping; `specific`
   scope honors `workload_ids`).
3. For each workload, runs the enabled micro-checks and records a
   `MicroValidationRun` (status, per-check results, restore-point age, duration).
4. On a failing run, counts consecutive non-passing runs for that workload and,
   once it reaches `consecutive_failures_before_alert`, raises a
   `ValidationAlert` (deduped against any unresolved alert for the same policy +
   workload).

### Micro-checks
Pure, unit-tested evaluators in `continuous_validation.py`:

| Check | Source | Status logic |
|---|---|---|
| restore_point_freshness | `workload.last_backup_at` vs RPO | pass <= RPO, warn <= 2x, fail beyond / missing |
| rpo_compliance | same age vs RPO (strict SLA) | pass <= RPO, warn <= 1.5x, fail beyond / missing |
| agent_heartbeat | `appliance.last_heartbeat` vs interval | pass <= 2x interval, warn <= 4x, fail beyond / missing |

Live-only checks (`mount_check`, `veeam_job_status`, `vcenter_connectivity`)
require appliance/Veeam/vCenter telemetry the SaaS side does not hold, so they
are recorded as `skipped` and ignored by the overall status until the appliance
submits real results (tracked with ADR-003).

---

## Tests

- Unit: thresholds for every evaluator, `build_check_results` (skips live/disabled
  checks), and `evaluate_check_results` ignoring skipped checks.
- Integration (real Postgres): seeds a policy + a workload with a stale restore
  point, runs the job twice, and asserts two failing `MicroValidationRun` rows and
  one `consecutive_failures` `ValidationAlert`.

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
