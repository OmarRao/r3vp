# Phase 12: DR Runbook Automation

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 12 transforms R3VP from a validation tool into an operational DR execution platform. Runbooks define the exact sequence of workloads to recover, the dependencies between them, parallel execution groups, notification steps, manual approval gates, and failure handling policies. When an incident occurs, a single click executes the full runbook through a Temporal workflow with live step-by-step progress.

---

## Scenarios

| Scenario | Use Case |
|---|---|
| ransomware | Full environment recovery after ransomware encryption event |
| datacenter_failure | Failover from a failed primary data center to DR site |
| cloud_outage | Regional cloud provider outage, recover to alternate region |
| site_failover | Geographic site failover for business continuity |
| custom | Any bespoke recovery scenario |

---

## Step Types

| Step Type | Description |
|---|---|
| recover_workload | Trigger a full recovery test for a specific workload via existing Temporal workflow |
| health_check | Run post-recovery health checks across one or more workloads |
| notify | Send a message to a Slack webhook, Teams webhook, or email |
| wait | Pause execution for a specified number of minutes (DNS propagation, replication lag) |
| manual_gate | Pause and wait for a human to approve before continuing |
| run_script | Execute a shell script on the appliance (DNS cutover, firewall rule update, etc.) |

---

## Execution Model

### Wave-based dependency resolution

Steps declare dependencies via `depends_on_seq` (list of seq numbers that must complete first). The engine performs a topological sort and groups independent steps into waves. Steps within a wave marked `parallel: true` execute concurrently.

Example: a 12-step ransomware runbook resolves into 4 waves:
- Wave 1: Recover critical infrastructure (AD, auth)
- Wave 2: Recover application tier in parallel (SQL, ERP)
- Wave 3: Verify, notify, await manual DNS confirmation
- Wave 4: Recover secondary systems, final validation, CISO notification

### Failure policies

Each step declares `on_failure`:
- `stop` - halt execution and mark the run as failed
- `continue` - log the failure and proceed to the next step
- `rollback` - mark the run as rolled_back (triggers saga compensation in future)

### RTO tracking

Execution start time is captured when the Temporal workflow begins. Completion time is recorded when the final step finishes. Actual RTO in minutes is computed and compared to the runbook's `rto_target_mins`. `rto_met: true/false` is stored on the execution record.

---

## Temporal Workflow

`RunbookWorkflow` in `apps/appliance/src/workflows/runbook_workflow.py`:

1. `fetch_execution_plan` activity: fetches all steps for the execution from the API
2. For each step in seq order: `execute_step` activity dispatches based on `step_type`
3. `update_step_status` activity posts the result back to the API after each step
4. `finalize_execution` activity marks the execution complete/failed with actual RTO

Activities use a 2-attempt retry policy except `execute_step` (no retry, result is authoritative).

---

## API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/runbooks` | workloads:read | List runbooks |
| POST | `/api/v1/runbooks` | workloads:write | Create runbook with steps |
| GET | `/api/v1/runbooks/{id}` | workloads:read | Get runbook with execution plan |
| POST | `/api/v1/runbooks/{id}/execute` | test_runs:trigger | Trigger execution |
| GET | `/api/v1/runbooks/{id}/executions` | test_runs:read | Execution history |
| GET | `/api/v1/runbooks/executions/{id}/steps` | test_runs:read | Live step status |

---

## Database Migration 0013

Four tables: `runbooks`, `runbook_steps`, `runbook_executions`, `runbook_execution_steps`.

`runbook_steps.depends_on_seq` is a JSONB array of integer seq numbers. `runbook_steps.config` is a JSONB object with step-type-specific fields. Cascade delete from runbook to steps and from execution to execution steps.

---

## Example Runbook Definition

```json
{
  "name": "Full Ransomware Recovery",
  "scenario": "ransomware",
  "rto_target_mins": 240,
  "tags": ["critical", "production"],
  "steps": [
    {"seq": 1, "name": "Recover domain controller", "step_type": "recover_workload", "workload_id": "...", "depends_on_seq": [], "timeout_mins": 60, "on_failure": "stop"},
    {"seq": 2, "name": "Recover auth service", "step_type": "recover_workload", "workload_id": "...", "depends_on_seq": [1], "timeout_mins": 45, "on_failure": "stop"},
    {"seq": 3, "name": "Recover SQL cluster", "step_type": "recover_workload", "workload_id": "...", "depends_on_seq": [2], "parallel": true, "timeout_mins": 60, "on_failure": "stop"},
    {"seq": 4, "name": "Recover ERP", "step_type": "recover_workload", "workload_id": "...", "depends_on_seq": [2], "parallel": true, "timeout_mins": 90, "on_failure": "continue"},
    {"seq": 5, "name": "Wait for DNS propagation", "step_type": "wait", "depends_on_seq": [3, 4], "config": {"duration_mins": 5}},
    {"seq": 6, "name": "Notify incident channel", "step_type": "notify", "depends_on_seq": [5], "config": {"channel": "slack", "destination": "https://hooks.slack.com/...", "message": "Core systems restored"}},
    {"seq": 7, "name": "Confirm VPN access", "step_type": "manual_gate", "depends_on_seq": [6], "config": {"instructions": "Confirm VPN access is restored before proceeding"}},
    {"seq": 8, "name": "Final health check", "step_type": "health_check", "depends_on_seq": [7], "timeout_mins": 15, "on_failure": "stop"},
    {"seq": 9, "name": "Notify CISO", "step_type": "notify", "depends_on_seq": [8], "config": {"channel": "email", "destination": "ciso@acmecorp.com", "message": "DR exercise complete"}}
  ]
}
```

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
