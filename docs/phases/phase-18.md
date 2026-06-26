# Phase 18: Continuous Validation Mode

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 18 adds always-on micro-validation that runs lightweight checks against every workload on a configurable interval (default: every 15 minutes) without triggering a full instant recovery test. Silent backup failures, stale restore points, and broken Veeam jobs are detected hours before they would surface in a scheduled full test.

---

## Micro-Checks

Six check types run per interval:

| Check | Category | What It Verifies |
|---|---|---|
| restore_point_freshness | Data Protection | Latest restore point is within the configured RPO window |
| mount_check | Connectivity | Recovery mount endpoint responds within 5 seconds |
| veeam_job_status | Backup Health | Last Veeam backup job completed with Success or Warning status |
| agent_heartbeat | Appliance Health | R3VP appliance reported a heartbeat within the last interval |
| vcenter_connectivity | Connectivity | Appliance can reach vCenter and enumerate the protected VM |
| rpo_compliance | SLA Compliance | Current RPO exposure vs the workload RPO target |

Each check returns `pass`, `warn`, or `fail` with a detail string and optional measured value.

---

## Validation Policies

A `ContinuousValidationPolicy` defines:
- Which workloads to check (`all`, `tag:critical`, `specific` with a list of IDs)
- How frequently to check (`check_interval_mins`, minimum 1 minute)
- Which of the 6 checks to enable per policy
- Alert behavior: `alert_on_failure` and `consecutive_failures_before_alert`

Multiple policies can run simultaneously, allowing different cadences for critical vs non-critical workloads (e.g. every 5 minutes for Tier 1, every 30 minutes for Tier 2).

---

## Alerting

`ValidationAlert` records are created when:
- A check fails and `alert_on_failure` is true
- Consecutive failures reach `consecutive_failures_before_alert`
- A restore point exceeds the RPO window (`restore_point_stale`)
- A Veeam job fails (`veeam_job_failed`)

Alerts are resolved manually via `POST /v1/continuous-validation/alerts/{id}/resolve` or automatically when the next check passes.

---

## Rolling Health

`GET /v1/continuous-validation/health` computes rolling status from the last 100 micro-validation runs:

| Status | Condition |
|---|---|
| healthy | Pass rate >= 90% |
| degraded | Pass rate 70-89% |
| failing | Pass rate < 70% |

`consecutive_failures` counts how many of the most recent runs were non-passing, used to determine alert escalation.

---

## Comparison to Full Recovery Tests

| Dimension | Micro-Validation | Full Recovery Test |
|---|---|---|
| Duration | Seconds | 15-90 minutes |
| Frequency | Every 5-30 minutes | Weekly or monthly |
| Disruption | Zero (read-only checks) | Isolated network spinup |
| Validates | Backup freshness, connectivity, job health | Actual OS boot, application health, RTO measurement |
| Purpose | Early warning detection | Compliance evidence, RTO/RPO proof |

Micro-validation does not replace full recovery tests. It surfaces problems early so full tests always pass.

---

## API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/v1/continuous-validation/checks` | none | List all available micro-checks |
| GET | `/v1/continuous-validation/policies` | workloads:read | List validation policies |
| POST | `/v1/continuous-validation/policies` | workloads:write | Create policy |
| PATCH | `/v1/continuous-validation/policies/{id}/toggle` | workloads:write | Enable or disable policy |
| GET | `/v1/continuous-validation/runs` | workloads:read | Recent micro-validation run results |
| GET | `/v1/continuous-validation/health` | workloads:read | Rolling health summary |
| GET | `/v1/continuous-validation/alerts` | workloads:read | Active or resolved alerts |
| POST | `/v1/continuous-validation/alerts/{id}/resolve` | workloads:write | Resolve an alert |

---

## Database Migration 0019

Three tables:
- `continuous_validation_policies`: org-scoped policies with interval, scope, enabled checks, and alert config
- `micro_validation_runs`: per-run records with check-level results JSONB, restore point age, duration, and alert_sent flag
- `validation_alerts`: alert records with type, severity, resolution tracking; cascades on policy delete

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
