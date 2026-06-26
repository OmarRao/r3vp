# Phase 16: MSSP Console

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 16 adds a multi-tenant MSSP (Managed Security Service Provider) console that lets a single operator manage multiple customer organizations from one portal. MSSPs and IT service providers can view cross-org readiness rollups, drill into per-customer scorecards, define alert rules that fire across all customers, and onboard new customer orgs without switching accounts.

---

## Customer Organization Management

Each customer org is tracked as an `MsspCustomerOrg` record linked to an `MsspPartner`. Customers are tagged with a tier (standard, premium, enterprise) and free-form tags for filtering and alert targeting.

The customer table shows per-org readiness score, workload count, active threat count, last test date, and overall health status (healthy, warning, critical) in a single view.

---

## Cross-Org Readiness Summary

The `/v1/mssp/summary` endpoint aggregates across all customer orgs for the partner:

| Metric | Description |
|---|---|
| total_customers | Total orgs under management |
| healthy / warning / critical | Count by health bucket |
| avg_readiness_score | Mean score across all orgs |
| total_workloads | Sum of workloads under management |
| total_active_threats | Active threat findings across all orgs |
| total_open_incidents | Open incidents across all orgs |

---

## Per-Customer Scorecard

`GET /v1/mssp/customers/{id}/scorecard` returns the customer's current readiness score, 6-month trend, workload stats, and top-risk workloads ranked by RTO proximity. MSSPs use this for customer QBRs and reporting.

---

## Alert Rules

`MsspAlertRule` defines automated alerting conditions that apply across all or a subset of customer orgs:

| Condition | Description |
|---|---|
| readiness_below | Alert when a customer's overall score drops below threshold |
| rto_breach | Alert when any workload misses its RTO target |
| test_failure | Alert when a recovery test fails |
| no_test_in_days | Alert when a customer has no tests in N days |
| threat_detected | Alert when a new threat finding is confirmed |

Rules can be scoped: `all`, `tier:premium`, `tag:critical`, etc.

---

## API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/v1/mssp/summary` | mssp:read | Cross-org readiness summary |
| GET | `/v1/mssp/customers` | mssp:read | List customer orgs |
| POST | `/v1/mssp/customers` | mssp:manage | Add customer org |
| DELETE | `/v1/mssp/customers/{id}` | mssp:manage | Remove customer org |
| GET | `/v1/mssp/customers/{id}/scorecard` | mssp:read | Per-customer scorecard with trend |
| GET | `/v1/mssp/alert-rules` | mssp:read | List alert rules |
| POST | `/v1/mssp/alert-rules` | mssp:manage | Create alert rule |

---

## Database Migration 0017

Three tables:
- `mssp_partners`: partner profile with white-label branding fields (logo_url, primary_color), plan, and max_customer_orgs limit
- `mssp_customer_orgs`: customer org records with tier, tags, notes, onboarded_at; cascades on partner delete
- `mssp_alert_rules`: alert conditions scoped to a partner with notification channel config; cascades on partner delete

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
