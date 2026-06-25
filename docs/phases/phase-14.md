# Phase 14: Billing and Usage Metering

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 14 adds Stripe-backed subscription management and per-period usage metering. Three plan tiers cover the range from small teams to enterprise MSSPs. The billing portal shows current plan, workload consumption, usage history, and downloadable invoices. A Stripe webhook handler keeps subscription state in sync with payment lifecycle events.

---

## Plans

| Plan | Price | Workload Limit | Key Features |
|---|---|---|---|
| Starter | $499/month | 10 | All providers, SOC 2 / ISO 27001, email support |
| Growth | $1,499/month | 50 | All frameworks, RBAC + SSO, API keys, integrations, priority support |
| Enterprise | $25/workload/month | Unlimited | MSSP console, custom SLA, dedicated CSM, on-prem option |

---

## Usage Metering

`UsageRecord` snapshots are captured per billing period and track:
- Workloads active
- Test runs executed
- Compliance reports generated
- Evidence bundles created
- API calls made

Metering is org-scoped. Records persist across periods for billing history and trend analysis.

---

## Stripe Integration

The billing service wraps three Stripe operations:
- `create_stripe_customer`: creates a Customer object for the org
- `create_checkout_session`: returns a hosted Checkout URL for plan upgrades
- `cancel_subscription`: sets `cancel_at_period_end: true` on the Stripe subscription

Stripe secret key and price IDs are read from environment variables (`STRIPE_SECRET_KEY`, `STRIPE_PRICE_STARTER`, `STRIPE_PRICE_GROWTH`, `STRIPE_PRICE_ENTERPRISE`). If not set, checkout returns a 503 with a configuration hint.

---

## Webhook Handler

`POST /v1/billing/webhook` handles:
- `customer.subscription.updated`: syncs status (active, past_due, cancelled) to the `subscriptions` table
- `invoice.paid`: creates an `Invoice` record with period, amount, and hosted PDF URL

Webhook signature verification uses `STRIPE_WEBHOOK_SECRET`. Falls back to unsigned parsing in dev when the secret is not set.

---

## API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/v1/billing/plans` | none | Public plan catalog |
| GET | `/v1/billing/subscription` | settings:read | Current subscription status |
| GET | `/v1/billing/usage` | settings:read | Usage records for last 6 periods |
| GET | `/v1/billing/invoices` | settings:read | Invoice history (last 12) |
| POST | `/v1/billing/checkout` | settings:write | Create Stripe Checkout session |
| POST | `/v1/billing/webhook` | none (Stripe signature) | Stripe lifecycle events |

---

## Database Migration 0015

Three tables:
- `subscriptions`: plan, status, Stripe IDs, workload limit/count, trial and period dates
- `usage_records`: per-period counters for all tracked dimensions with JSONB breakdown
- `invoices`: Stripe invoice mirror with amount, status, PDF URL, and paid timestamp

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
