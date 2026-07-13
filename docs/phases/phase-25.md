# Phase 25: MSSP Usage Metering and Billing

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

The MSSP console managed customer orgs and rolled up their posture, but there
was no way to meter or bill customer usage. Phase 25 adds real usage metering
and a priced billing summary across the partner's customer portfolio.

---

## What Changed

### Billing service (`services/mssp_billing.py`)
Pure and unit-tested. A per-tier monthly rate card (base fee + per-workload +
per-recovery-test) prices each customer's usage into a line item, and the line
items roll up into a portfolio summary (customer count, total workloads, total
test runs, total due).

| Tier | Base | Per workload | Per test run |
|---|---|---|---|
| standard | $0 | $5.00 | $0.50 |
| premium | $200 | $8.00 | $0.75 |
| enterprise | $500 | $12.00 | $1.00 |

Unknown tiers fall back to standard pricing.

### Endpoint
`GET /v1/mssp/billing?period_days=N` (default 30, 1-366). For each of the
partner's `MsspCustomerOrg` rows it counts distinct protected workloads and test
runs started within the period (scoped through the customer org's appliances),
prices them, and returns line items plus the summary. Gated on `mssp:read`.

### RBAC fix
The MSSP router required `mssp:read` / `mssp:manage`, but those permissions were
absent from the RBAC catalog, so `require_permission` denied every role
(including owner) and the whole router returned 403. Both permissions were added
to the catalog and are auto-granted to owner and admin through the system-role
derivation.

---

## Tests

- Unit: rate-card fallback, standard/premium line-item math, unknown-tier
  normalization, and portfolio summary roll-up.
- Integration (real Postgres): seeds a partner, a customer org, an appliance,
  a workload, and a test run, then asserts the billing endpoint returns 200 (not
  the previous 403), meters one workload and one run, and prices the premium
  line item correctly.

---

## Notes

`MsspCustomerOrg.mssp_id` is a foreign key to `mssp_partners.id`, while the
router convention (create/list/billing) treats it as the partner's org id. A
follow-up should formalize partner provisioning (map a partner org to its
`MsspPartner` row) so customer creation does not depend on a partner row whose id
equals the org id.

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*
