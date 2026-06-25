# Phase 13: Self-Service Onboarding Wizard

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 13 adds a guided, in-product onboarding wizard that takes a new organization from signup to first validated recovery test without requiring professional services. The six-step flow covers org profile, appliance deployment, Veeam connection, workload discovery, and first test execution.

---

## Steps

| Step | ID | Title | Key Action |
|---|---|---|---|
| 1 | org_profile | Organization Profile | Set org name, industry, default RTO/RPO targets |
| 2 | deploy_appliance | Deploy Appliance | Docker or OVA deployment with registration token |
| 3 | connect_veeam | Connect Veeam | Enter Veeam B&R host, port, and credentials |
| 4 | discover_workloads | Discover Workloads | Trigger inventory sync from Veeam and vCenter |
| 5 | first_test | Run First Validation | Select a workload and trigger first recovery test |
| 6 | complete | Setup Complete | Onboarding confirmed, redirect to dashboard |

---

## Progress Model

Session progress is computed from `step_data` stored on `OnboardingSession`. Each step has a completion predicate:

| Step | Completion Condition |
|---|---|
| org_profile | `step_data.org_name` is set |
| deploy_appliance | `step_data.appliance_id` is set |
| connect_veeam | `step_data.veeam_connected` is true |
| discover_workloads | `step_data.workload_count` > 0 |
| first_test | `step_data.first_test_run_id` is set |
| complete | Always true |

Auto-complete fires when current_step advances to 6 and overall progress is >= 80%.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/v1/onboarding` | Get session status, auto-creates session on first call |
| POST | `/v1/onboarding/step` | Advance a step with result data |
| POST | `/v1/onboarding/dismiss` | Hide wizard without completing |
| POST | `/v1/onboarding/reset` | Reset to step 1 for re-onboarding |

---

## Database Migration 0014

Table: `onboarding_sessions`
- `id` UUID primary key
- `org_id` UUID unique (one session per org)
- `current_step` integer, default 1
- `completed` boolean
- `dismissed` boolean
- `step_data` JSONB storing per-step completion evidence
- `started_at`, `completed_at` timestamps
- `created_by` FK to users

---

## Security Note

Credentials entered in step 3 (Veeam connection) are encrypted with SOPS and age on the appliance side and never transmitted to the SaaS backend. The wizard only stores a `veeam_connected: true` flag as completion evidence.

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
