# R3VP System Architecture

R3VP validates ransomware recovery readiness by running automated,
isolated recovery tests against real backups and scoring the results. It
is split across a customer-hosted appliance and a cloud-hosted SaaS so that
customer credentials never leave the customer environment.

Related decisions: [ADR-001 Appliance runtime](adr/001-appliance-runtime.md),
[ADR-002 Temporal workflow engine](adr/002-temporal-workflow-engine.md),
[ADR-003 Veeam/vCenter recovery connector](adr/003-veeam-vcenter-recovery-connector.md).

## System context

```mermaid
flowchart LR
  subgraph customer["Customer environment"]
    veeam["Veeam Backup & Replication"]
    vcenter["VMware vCenter / Hyper-V"]
    appliance["R3VP Appliance<br/>(Python, Temporal worker, YARA)"]
    sandbox["Isolated recovery sandbox"]
    appliance --> veeam
    appliance --> vcenter
    appliance --> sandbox
  end

  subgraph saas["R3VP SaaS (cloud)"]
    api["API (FastAPI)"]
    db[("PostgreSQL<br/>inventory, runs, evidence")]
    portal["Portal (Next.js + Auth0)"]
    api --> db
    portal --> api
  end

  subgraph external["External systems"]
    integrations["Slack / PagerDuty<br/>ServiceNow / SIEM"]
    auth0["Auth0"]
  end

  appliance -- "outbound mTLS, HTTPS only" --> api
  portal --> auth0
  api --> integrations

  operator(["Operator / CISO"]) --> portal
```

Key property: the appliance dials **out** to the SaaS over mutually
authenticated TLS. The SaaS never opens a connection into the customer
network, and backup/hypervisor credentials stay inside the appliance.

## Component responsibilities

| Component | Stack | Responsibility |
|-----------|-------|----------------|
| Appliance | Python, Temporal worker, pyVmomi, YARA | Discovers protected workloads, selects restore points, runs isolated recovery tests, measures actual RTO/RPO, scans restored data for ransomware, captures evidence, tears down the sandbox |
| API | FastAPI, SQLAlchemy (async), Alembic | Asset inventory, readiness scoring, RBAC, reporting, integrations, MSSP multi-tenant management |
| Database | PostgreSQL 16 | Workloads, test runs and steps, health checks, threat scans/findings, scorecards, audit chain |
| Portal | Next.js 15, Auth0, Firebase | Dashboards, scorecards, evidence, admin |
| Workflow engine | Temporal | Durable orchestration of the multi-step recovery test workflow |

## Recovery-test data flow

```mermaid
sequenceDiagram
  participant P as Portal
  participant A as API
  participant Ap as Appliance
  participant V as Veeam / vCenter
  participant S as Sandbox

  P->>A: Schedule / trigger validation
  A->>Ap: Enqueue test (outbound poll / job)
  Ap->>V: Select restore point, start instant recovery
  V-->>S: Restore workload into isolated network
  Ap->>S: Boot, run OS + application health checks
  Ap->>S: YARA / entropy scan for ransomware indicators
  Ap->>Ap: Measure actual RTO / RPO, capture evidence
  Ap->>V: Tear down temporary recovery
  Ap->>A: Report run result + evidence (mTLS)
  A->>A: Update readiness score, trend, threats
  A-->>P: Updated dashboard / scorecard
```

## Readiness score

The composite readiness score (0-100) is computed in
`apps/api/src/services/readiness_scoring.py` and
`services/executive_report.py`:

- 40% coverage (workloads tested / total)
- 35% pass rate (workloads passing / tested)
- 15% RTO compliance (passed runs meeting their RTO target)
- up to 10-point penalty for active threats and open incidents

## Trust and isolation boundaries

```mermaid
flowchart TB
  subgraph b1["Customer trust boundary"]
    creds["Backup + hypervisor credentials<br/>(encrypted at rest, never exported)"]
    appliance2["Appliance"]
    creds --> appliance2
  end
  subgraph b2["SaaS trust boundary"]
    api2["API + Postgres"]
  end
  appliance2 -- "mTLS, outbound only (no inbound)" --> api2
```
