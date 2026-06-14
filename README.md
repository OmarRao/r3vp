# R3VP — Ransomware Readiness & Recovery Validation Platform

Automated ransomware recovery validation: deploy a lightweight appliance, connect it to Veeam B&R and VMware vCenter, and continuously prove that your critical workloads can actually be recovered within their RTO/RPO targets.

## Architecture

```
Customer Environment                    SaaS Platform (Cloud)
─────────────────────────────────       ──────────────────────────────
Validation Appliance (OVA/Docker)  ──►  API Gateway (mTLS)
  ├─ Veeam B&R connector                 ├─ Appliance Relay Service
  ├─ vCenter connector                   ├─ Workflow Orchestrator
  ├─ Temporal workflow worker            ├─ Readiness Scoring Engine
  ├─ Credential vault (SOPS)             ├─ PostgreSQL (RDS)
  └─ Evidence collector                  ├─ S3 (evidence artifacts)
                                         └─ Web Portal (Next.js)
```

Credentials **never leave the customer environment**. The appliance communicates outbound-only via mutual TLS.

## Repository Structure

```
r3vp/
├── apps/
│   ├── appliance/      # On-prem validation appliance (Python + Temporal)
│   ├── api/            # SaaS backend (FastAPI + PostgreSQL)
│   └── portal/         # Web dashboard (Next.js 14)
├── packages/
│   └── shared-types/   # TypeScript types shared between portal and API
├── infra/
│   ├── terraform/      # AWS infrastructure (RDS, S3, ECS, CloudFront)
│   └── k8s/            # Helm charts
├── scripts/            # mTLS cert generation, OVA build
└── docs/
    ├── adr/            # Architecture Decision Records
    ├── api-spec/       # OpenAPI specs
    └── runbooks/
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ with [uv](https://github.com/astral-sh/uv)
- Node.js 20+ with pnpm
- Access to a Veeam B&R server and VMware vCenter

### Local Development

```bash
# Install all Python dependencies
uv sync

# Start the API + PostgreSQL locally
cd apps/api && docker compose up -d

# Start the portal
cd apps/portal && pnpm install && pnpm dev

# Run the appliance in dev mode
cd apps/appliance && uv run python -m src.main --dev
```

### Deploy Appliance

```bash
# Generate mTLS certificates for a new appliance
./scripts/gen-mtls-certs.sh <org-id> <appliance-name>

# Deploy via Docker Compose
cd apps/appliance && docker compose up -d
```

## Development Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Monorepo scaffold, mTLS channel, appliance registration | 🔄 In Progress |
| 2 | Veeam + vCenter discovery, inventory sync | ⏳ Pending |
| 3 | Recovery test workflow engine | ⏳ Pending |
| 4 | Health checks & evidence capture | ⏳ Pending |
| 5 | Readiness scoring, dashboard, reports | ⏳ Pending |
| 6 | OVA packaging, hardening, GA | ⏳ Pending |

## License

Proprietary — Veeam Software Corporation
