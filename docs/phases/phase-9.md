# Phase 9: Executive Reporting and CISO Scorecard

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 9 gives CISOs and board-level stakeholders a single-number readiness score backed by trend data, provider breakdown, and a ranked risk list. The scorecard is generated as a signed PDF and delivered automatically on a weekly, monthly, or quarterly digest schedule.

---

## Readiness Score Formula

```
score = (coverage * 0.40) + (pass_rate * 0.35) + (rto_compliance * 0.15) - threat_penalty
```

| Component | Weight | Definition |
|---|---|---|
| Coverage | 40% | workloads_tested / workloads_total |
| Pass rate | 35% | workloads_passing / workloads_tested |
| RTO compliance | 15% | % of tests where actual RTO <= target |
| Threat penalty | deducted | min(active_threats + open_incidents, 10) |

Score range: 0-100. Color thresholds: green (80+), amber (60-79), red (<60).

---

## Scorecard PDF Contents

1. Cover: org name, period label, generation timestamp
2. Score hero: large number with color coding and pass rate summary
3. KPI row: workloads passing, RTO compliance %, active threats, open incidents
4. Score trend table: last 6 snapshots with date, score, workload counts, RTO %
5. Provider breakdown: per-provider tested/total and pass rate
6. Top risks: up to 5 workloads ranked by risk with severity and reason
7. Footer: attribution, R3VP version

SHA-256 of the PDF is returned in the `X-SHA256` response header.

---

## Digest Schedules

`DigestSchedule` model configures automatic scorecard delivery:

| Field | Description |
|---|---|
| cadence | weekly, monthly, or quarterly |
| recipients | list of email addresses |
| include_scorecard | attach PDF scorecard |
| include_trend_chart | include trend section in email body |
| include_provider_breakdown | include provider table |
| include_top_risks | include risk ranking |
| enabled | pause/resume without deleting |

---

## API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/executive/scorecard` | reports:read | Latest scorecard snapshot |
| GET | `/api/v1/executive/trend` | reports:read | Score trend, last N months |
| POST | `/api/v1/executive/scorecard/pdf` | reports:generate | Download signed scorecard PDF |
| GET | `/api/v1/executive/digest-schedules` | reports:read | List digest schedules |
| POST | `/api/v1/executive/digest-schedules` | reports:schedule | Create digest schedule |
| DELETE | `/api/v1/executive/digest-schedules/{id}` | reports:schedule | Delete schedule |

---

## Database Migration 0011

```sql
CREATE TABLE digest_schedules (
    id                       UUID PRIMARY KEY,
    org_id                   UUID NOT NULL,
    cadence                  VARCHAR(20) NOT NULL,
    recipients               JSONB DEFAULT '[]',
    include_scorecard        BOOLEAN DEFAULT true,
    include_trend_chart      BOOLEAN DEFAULT true,
    include_provider_breakdown BOOLEAN DEFAULT true,
    include_top_risks        BOOLEAN DEFAULT true,
    enabled                  BOOLEAN DEFAULT true,
    last_sent_at             TIMESTAMPTZ,
    created_at               TIMESTAMPTZ DEFAULT now(),
    created_by               UUID REFERENCES users(id)
);

CREATE TABLE scorecard_snapshots (
    id                 UUID PRIMARY KEY,
    org_id             UUID NOT NULL,
    snapshot_date      VARCHAR(10) NOT NULL,
    overall_score      INTEGER NOT NULL,
    workloads_total    INTEGER DEFAULT 0,
    workloads_tested   INTEGER DEFAULT 0,
    workloads_passing  INTEGER DEFAULT 0,
    rto_compliance_pct INTEGER DEFAULT 0,
    active_threats     INTEGER DEFAULT 0,
    open_incidents     INTEGER DEFAULT 0,
    provider_breakdown JSONB DEFAULT '{}',
    top_risks          JSONB DEFAULT '[]',
    created_at         TIMESTAMPTZ DEFAULT now()
);
```

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
