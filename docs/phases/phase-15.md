# Phase 15: Appliance Fleet Management

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 15 extends R3VP to support multi-site deployments with 10+ appliances. Organizations can group appliances by site or region, monitor per-appliance health in real time, push configuration templates to groups of appliances simultaneously, and view a unified cross-site readiness summary.

---

## Fleet Overview

The fleet overview endpoint aggregates health across all appliances for a given org:
- Total appliance count with healthy / warning / offline breakdown
- Per-appliance status, resource utilization (CPU, memory, disk), connection state for Veeam, vCenter, and Temporal, workload count, version, and last test run time

---

## Appliance Health Status

| Status | Condition |
|---|---|
| healthy | All connections up, no alerts |
| warning | At least one connection degraded or a resource threshold exceeded |
| offline | No heartbeat received; all connections reported down |
| degraded | Partial connectivity; reduced functionality |

Health snapshots are stored in `appliance_health_snapshots` with a full set of boolean connection flags, resource percentages, and a JSONB alerts array.

---

## Site Groups

`ApplianceGroup` organizes appliances by site or deployment type (e.g. "NYC Sites", "Cloud Sites", "DR Appliances"). Each group stores:
- `site_name` and `region` for display
- `config_template` JSONB pushed to member appliances on bulk sync
- `tags` for filtering

Members are tracked in `appliance_group_members` with cascade delete when a group or appliance is removed.

---

## Bulk Configuration Push

`POST /v1/fleet/bulk-config` accepts a list of appliance IDs and a config dict and creates a `BulkConfigJob`. The job is consumed by appliance-side polling. Results per appliance (ok / error) are stored in the `results` JSONB array.

Example config payload:
```json
{
  "default_rto_target_mins": 60,
  "sync_interval_mins": 30,
  "log_level": "info"
}
```

---

## API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/v1/fleet/overview` | appliances:read | Fleet summary with per-appliance health |
| GET | `/v1/fleet/health` | appliances:read | Latest health snapshots |
| GET | `/v1/fleet/groups` | appliances:read | List site groups |
| POST | `/v1/fleet/groups` | appliances:manage | Create site group |
| POST | `/v1/fleet/bulk-config` | appliances:manage | Push config to selected appliances |
| GET | `/v1/fleet/bulk-config/{job_id}` | appliances:read | Check config push job status |

---

## Database Migration 0016

Four tables:
- `appliance_groups`: org-scoped groups with site/region metadata and config template
- `appliance_group_members`: many-to-many join with cascade deletes
- `appliance_health_snapshots`: timestamped health readings per appliance with full resource and connection state
- `bulk_config_jobs`: async config push jobs with per-appliance result tracking

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
