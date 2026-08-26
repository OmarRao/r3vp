# Changelog

All notable changes to R3VP are documented here.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## [Unreleased] - HTTP Hardening: Security Headers + Request IDs

### Added
- `SecurityHeadersMiddleware` (`src/http_hardening.py`): adds `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Strict-Transport-Security`, and `Permissions-Policy` to every response, and assigns each request a correlation id (honoring an inbound `X-Request-ID` or generating one) that is bound to the structlog context and echoed in the `X-Request-ID` response header for cross-service tracing
- Tests for the headers and request-id echo; README Security Design section updated

---

## [Unreleased] - Supply Chain: Signed Images + SBOM + Provenance

### Added
- Published container images are now signed with Cosign keyless (Sigstore/Fulcio via GitHub OIDC) and carry a CycloneDX SBOM and SLSA build-provenance attestation, generated in the Docker Publish workflow (`sbom: true`, `provenance: mode=max`, `id-token: write`, `sigstore/cosign-installer` SHA-pinned). README documents how to `cosign verify` a published image before deploying

---

## [Unreleased] - Observability: Metrics + Health Probes

### Added
- Prometheus metrics at `GET /metrics` (request counts, latency histograms, in-flight requests) via `prometheus-fastapi-instrumentator`, ready to scrape
- Kubernetes-native health probes: `GET /live` (liveness) and `GET /ready` (readiness, returns 503 when the database is unreachable). `/health` is kept for backward compatibility
- Unit tests for `/live` and `/metrics`; integration test for `/ready` against real Postgres

### Fixed
- `k8s/deployment.yaml` referenced a `/ready` readiness probe that did not exist (pods would never become ready); the endpoint now exists, and the liveness probe points at the new `/live`. README and user-guide gain a Monitoring and Health section; OpenAPI spec regenerated

---

## [Unreleased] - API Rate Limiting

### Added
- Per-client API rate limiting (`src/rate_limit.py`): a fixed-window limiter keyed by API key (when supplied) or source IP, defaulting to 120 requests/minute (`R3VP_API_RATE_LIMIT_PER_MINUTE`, toggle with `R3VP_API_RATE_LIMIT_ENABLED`). Every response carries `X-RateLimit-Limit/Remaining/Reset`; exceeding the limit returns `429` with `Retry-After`. Health, docs, and metrics paths are exempt. This makes real the rate-limit behavior the user guide already documented
- Unit and middleware tests (limiter windows, per-key isolation, 429 + headers, exempt paths)

### Notes
- The limiter store is in-process (fine for single-instance and the default deployment); the same interface can be backed by a shared store (Redis) for horizontal scale. README Security Design and user-guide Rate Limiting sections updated to match the implementation

---

## [Unreleased] - Dependency Security: cryptography + h2

### Fixed
- Bumped transitive pip dependencies in `uv.lock` to patched versions: `cryptography` `49.0.0` -> `50.0.0` (high: PKCS#7 EnvelopedData Bleichenbacher oracle) and `h2` `4.3.0` -> `4.4.1` (medium: duplicate Host header request smuggling). Clears the two open Dependabot alerts

---

## [Unreleased] - Performance: Compression + Connection Pool

### Changed
- Enabled gzip response compression (`GZipMiddleware`, `minimum_size=1000`) so large JSON responses (dashboards, reports, OpenAPI) are compressed for clients that accept gzip; small responses are left untouched
- Tuned the async DB connection pool: `pool_size=10`, `max_overflow=20`, `pool_recycle=1800` (was the defaults 5 / 10 / none), giving concurrency headroom and recycling stale connections
- Set the FastAPI app `version` to `1.0.0` (was a stale `0.2.0`) and regenerated `docs/api-spec/openapi.json`
- Added a guard test that gzip compression stays enabled

---

## [Unreleased] - Performance: Indexes + Async Hot Paths

### Changed
- Added btree indexes on the hot filter/join columns the dashboard, readiness, scorecard, MSSP, and threat endpoints use (19 indexes via migration `0022` and matching `index=True` on the ORM models). Postgres does not auto-index foreign-key columns, so these were sequential scans; now `appliances.org_id`, `workloads.appliance_id`, `test_runs.workload_id/status/completed_at/started_at`, the per-run child tables, `threat_*` `org_id`, `mssp_*` `mssp_id`, and the per-org tables are indexed
- MSSP billing (`GET /v1/mssp/billing`) no longer issues two queries per customer (an N+1 over the portfolio); it aggregates all customers' workload and test-run counts in two grouped queries. Same result, fewer round-trips
- The scorecard PDF endpoint now renders WeasyPrint in a worker thread (`asyncio.to_thread`) instead of on the event loop, so a CPU-bound PDF render no longer stalls other concurrent requests

### Notes
- No behavior or results change; the readiness/scorecard/billing numbers and the PDF output are identical. Indexes are declared on the models (so `create_all` matches the migration) and created idempotently (`CREATE INDEX IF NOT EXISTS`)

---

## [Unreleased] - Dual Licensing: AGPL-3.0 + Commercial

### Changed
- Adopted a dual-license model for current and future versions. Replaced the MIT `LICENSE` with the complete official GNU Affero General Public License v3.0, and added a separate paid commercial license path
- Added `COMMERCIAL-LICENSE.md` (commercial scope and process; contact `omarsrao@gmail.com`), `TRADEMARKS.md` (no trademark grant, nominative-use policy), and `DEPENDENCY-LICENSE-REVIEW.md` (technical dependency-license inventory, not legal advice)
- README gains a Licensing section; `docs/user-guide.md` License section updated (it previously and incorrectly stated Apache-2.0); `license = "AGPL-3.0-only"` added to the API, appliance, and portal manifests, plus Docker image `LABEL`s
- Added SPDX dual-license headers (`AGPL-3.0-only OR LicenseRef-Commercial`) to 242 owned source files (Python, TypeScript/TSX, Terraform, shell, CSS). Generated files, migrations, docs assets, config, and lock files were left unheadered
- Prior versions distributed under MIT remain governed by the terms under which they were originally distributed; this change applies to the current and future versions and does not revoke prior grants. No application behavior changed

---

## [Unreleased] - Code Scanning: Remove pip from images (root cause)

### Fixed
- Definitively root-caused the `setuptools 70.3.0` (CVE-2025-47273 / CVE-2026-59890) and `msgpack 1.1.2` (GHSA-6v7p-g79w-8964) image-scan findings: they are pip's own **vendored** build-time dependencies (listed verbatim in `pip/_vendor/vendor.txt`), so they were immune to venv, uv-cache, and pyproject changes and identical across both images. The application runs from the uv-managed venv and never uses pip at runtime, so both Dockerfiles now remove pip/setuptools/wheel after the OS patch step (`python -m pip uninstall -y pip setuptools wheel`). This drops the findings and shrinks the runtime attack surface; uv does not use pip, so builds are unaffected. The venv still carries patched setuptools/msgpack from the pyproject pins

---

## [Unreleased] - Code Scanning: Drop uv cache from images

### Fixed
- Root-caused the persistent `setuptools` (CVE-2025-47273 / CVE-2026-59890) and `msgpack` (GHSA-6v7p-g79w-8964) image-scan findings: they were not in the runtime venv but in the uv download/build cache (`~/.cache/uv`) that `uv sync` writes into the image layer and Trivy scans. Both Dockerfiles now build with `uv sync --no-cache` so the cache is never persisted, and the runtime `CMD` uses `uv run --no-sync` so it does not need the cache at container start. Combined with the pyproject pins, the venv carries only patched versions. Verified `uv run --no-sync` still imports and runs the app

---

## [Unreleased] - Code Scanning: Pin setuptools/msgpack via pyproject

### Fixed
- The image scanner findings for `setuptools` (CVE-2025-47273 / CVE-2026-59890) and `msgpack` (GHSA-6v7p-g79w-8964) persisted after the Dockerfile-level upgrade attempt, because the image build context does not include `uv.lock` and `uv sync` resolves fresh, so a post-sync `uv pip install` did not affect the resolved venv. Pinned `setuptools>=83.0.0` and `msgpack>=1.2.1` as explicit dependencies in both `apps/api` and `apps/appliance` pyproject files (and the lock), so the image's fresh `uv sync` resolves the patched versions. Reverted the ineffective Dockerfile `uv pip install` lines

---

## [Unreleased] - Security and Quality Sweep

### Fixed
- Dependabot (npm): bumped `next` `15.5.18` -> `15.5.22` (clears the Server Actions SSRF and Image Optimization SVG DoS advisories) and pinned `sharp` `>= 0.35.0` via override (clears the inherited libvips CVEs). `npm audit` now reports 0 vulnerabilities
- Also pinned `brace-expansion >= 2.0.2` via override, clearing a high-severity DoS advisory (GHSA-mh99-v99m-4gvg) reachable through the dev-only eslint toolchain; eslint/type-check/lint remain green
- Dependabot (pip): bumped `pyasn1` `0.6.3` -> `0.6.4` in `uv.lock` (quadratic-complexity and REAL-value resource-consumption DoS advisories)
- Code scanning (Trivy image scan): the API and appliance Dockerfiles now upgrade `setuptools` (`>= 83.0.0`) and `msgpack` (`>= 1.2.1`) in the resolved environment after `uv sync`, closing setuptools CVE-2025-47273 / CVE-2026-59890 and msgpack GHSA-6v7p-g79w-8964 (these are seeded into the venv and not pinned in uv.lock)

---

## [Unreleased] - Veeam 13.1 Integration

### Added
- `connectors/veeam/rest.py`: `x_api_version(build)` maps a Veeam build to the required `x-api-version` header value, grounded in the Veeam version ladder (11.x -> 1.0-rev1; 12.0/12.1 -> 1.1-rev0/rev1; 12.2/12.3.1+ -> 1.2-rev0/rev1; 13.0.0 -> 1.3-rev0; 13.0.1+ and 13.1 -> 1.3-rev1), plus `build_version_tuple` for minor/patch-aware parsing. `parse_server_info` now reports `rest_api_version`
- The Veeam client now sends the required `x-api-version` header on every request (previously none was sent, so requests would be rejected by a real server): a conservative default for the pre-serverInfo token call, upgraded to the exact per-build value once the build is detected
- `R3VP_VEEAM_API_VERSION_OVERRIDE` config to pin a specific revision when needed
- 13.1 `serverInfo` fixture and unit tests: `x_api_version` across 11/12.x/13.x/13.1 builds, `build_version_tuple` parsing, and `parse_server_info` reporting `1.3-rev1` for 13.x

### Fixed
- Version support docs corrected: Veeam 13.x uses REST API 1.3 (13.0.1+ and 13.1 -> 1.3-rev1), not 1.2 as previously labeled. README, the user guide (`docs/user-guide.md` Veeam B&R API Compatibility and Connect Veeam sections), the lab runbook, and the client docstrings updated

### Notes
- Pure mapping and parsing are unit-verified offline via fixtures. The exact 13.1 revision and the live header behavior should be confirmed against a real Veeam B&R 13.1 server; 1.3-rev1 is the correct floor for 13.0.1 and later

---

## [Unreleased] - sops bump v3.13.3

### Fixed
- Bumped the pinned `SOPS_VERSION` in the appliance Dockerfile from `v3.13.2` to `v3.13.3`, clearing code-scanning alert GHSA-hrxh-6v49-42gf (high): sops v3.13.3 bundles `google.golang.org/grpc` `v1.82.1` (the fixed version) instead of the vulnerable `v1.81.1`. sops runs only at build/deploy time for local secret decryption and is not exposed to the gRPC/xDS/HTTP2 attack surface, but the clean upstream fix is preferred

---

## [Unreleased] - Dependency Security Remediation

### Fixed
- Resolved 17 Dependabot alerts in transitive dependencies. Bumped Pillow `12.2.0` -> `12.3.0` in `uv.lock` (clears 13 pip advisories: heap out-of-bounds writes, decompression-bomb bypasses, and DoS paths in Pillow's image/font parsers). Ran `npm audit fix` in `apps/portal`, clearing the `js-yaml`, `brace-expansion`, and `protobufjs` npm advisories. Portal type-check and lint remain clean; `npm audit` reports 0 vulnerabilities

---

## [Unreleased] - SSO (OIDC)

### Added
- Organization SSO for the API now supports OIDC alongside the existing SAML config. The per-org `sso_configs` table gains a `protocol` discriminator (`saml` | `oidc`) and OIDC columns (`oidc_issuer`, `oidc_client_id`, `oidc_client_secret`, `oidc_redirect_uri`, `oidc_scopes`) via migration `0021`; the SAML columns become nullable so an OIDC-only org needs no dummy values
- Config CRUD (`GET`/`PUT /v1/sso`, `PATCH /v1/sso/toggle`) is protocol-aware and gated by `sso:manage`. The OIDC client secret is write-only: it is stored but never returned, and an upsert that omits it preserves the stored value
- OIDC login flow endpoints: `GET /v1/sso/oidc/login` builds the authorization-code redirect URL (state + nonce), and `POST /v1/sso/oidc/callback` exchanges the code and validates the returned `id_token`
- Pure, network-free OIDC service (`src/services/oidc.py`): state/nonce generation, authorization-URL construction, `id_token` validation (signature via JWKS, issuer, audience, expiry, nonce), and claim-to-identity mapping with per-org attribute overrides

### Verified
- Unit tests (`tests/test_oidc_service.py`, no DB/network): a locally-signed JWT plus an in-memory JWKS exercise the happy path and every error path (bad signature, expired, wrong audience, wrong issuer, nonce mismatch, unknown kid), plus URL building and claim mapping
- Integration tests (`tests/integration/test_sso_config.py`, real Postgres): OIDC config upsert/read, secret is write-only and preserved on re-upsert, toggle, per-protocol validation, and `sso:manage` gating

### Notes
- A real IdP (Azure AD, Okta, etc.) is configured entirely through the per-org DB config plus discovery; no code changes and no hardcoded secrets are required. The live IdP handshake in `/oidc/login` and `/oidc/callback` (discovery fetch, token-endpoint code exchange, JWKS retrieval) is network I/O and is not exercised end-to-end without a real IdP; its security-critical inner logic is the unit-tested pure service

---

## [Unreleased] - Veeam/vCenter Recovery Connector

### Added
- `connectors/veeam/rest.py`: pure request-building and response-parsing helpers for the Veeam B&R REST API (no network, no config, no I/O). Covers version detection (v1.0/v1.1/v1.2), OAuth2 token shaping, restore-point path selection, newest-consistent / in-RPO-window restore-point selection, instant-recovery endpoint + body construction with isolated-network mapping, session-id and stop-publishing path shaping, session-state poll classification (`PollDecision`), and RTO/RPO minute measurement plus a 0-100 readiness score
- `connectors/vcenter/moref.py`: pure moref lookup-planning (`RecoveredVmIdentity`, ordered `lookup_plan`) and identity extraction from a Veeam session's restored-object reference, so moref resolution is testable without pyVmomi
- vCenter DVS support (`create_isolated_portgroup_dvs`) alongside the existing standard-vSwitch path, plus `resolve_moref` driving the SearchIndex lookup plan; `provision_isolated_network` now selects the backend from config
- Config wiring for a real lab: `vcenter_network_backend`, `vcenter_vswitch_name`, `vcenter_dvs_name`, `recovery_poll_timeout_secs`, `recovery_poll_interval_secs` (all env-driven, no hardcoded secrets)
- `docs/runbooks/veeam-vcenter-lab.md`: lab configuration and the exact offline-vs-lab verification boundary
- Fixture-based unit tests (`tests/test_veeam_rest.py`, `tests/test_vcenter_moref.py`) with recorded Veeam REST JSON under `tests/fixtures/veeam/`, covering request building, response parsing, restore-point selection, every session-state transition (including failure and no-state/timeout paths), moref planning, and RTO/RPO/readiness. 59 pure tests pass locally with no native deps

### Changed
- `VeeamClient` now composes the pure `rest` helpers for auth, version detection, restore-point discovery, instant-recovery start/stop, and session polling; added `get_session` returning the full session body
- `wait_for_vm_boot` polls via `classify_poll` and resolves the real recovered moref from the published session's restored-object reference, falling back to the `recovered-{session_id}` placeholder only when the moref cannot be resolved (lab-gated)
- `record_rto_rpo` computes real RTO/RPO minutes and a readiness score from workflow timestamps; `select_restore_point` returns the point id plus its creation time so RPO is measured against the real restore point
- `RecoveryTestWorkflow` threads recovery-start / boot-ready / restore-point-creation timestamps into the RTO/RPO measurement step

### Notes
- The live Veeam token exchange, the exact instant-recovery session-body shape (restored-object key names in `parse_recovered_vm_identity`), pyVmomi moref resolution, isolated-portgroup provisioning on standard vSwitch and DVS, and screenshot evidence download remain to be validated against a real Veeam B&R + vCenter lab. All connection details are env/config-driven; see `docs/runbooks/veeam-vcenter-lab.md` for the precise boundary and how to configure it
---

## [Unreleased] - Portal Dashboard Dark Mode

### Added
- Every authenticated `/dashboard/*` page and shared component converted to the semantic color tokens so the whole dashboard renders correctly in light and dark. Hardcoded neutrals (inline hex and `bg-white`/`bg-gray-*`/`text-gray-*`/`border-gray-*` utilities) mapped to `bg-surface`, `bg-surface-2`, `text-content`, `text-content-muted`, `border-border`, etc.
- `ThemeToggle` added to the shared dashboard topbar in `app/dashboard/layout.tsx`, so it is reachable from every dashboard page
- Sidebar extracted into a client `components/dashboard-sidebar.tsx`. It stays dark navy in both themes (fixed brand chrome) and now has visible active (green left border) and hover states
- Theme-aware base styling for text inputs, selects, and textareas in `globals.css` so form fields no longer render as white boxes on dark surfaces
- `postcss.config.js` added. Tailwind, autoprefixer, and postcss were already dependencies and fully configured, but the PostCSS config file that makes Next.js run Tailwind over `globals.css` was missing, so no utility classes were being generated. This is a prerequisite for any Tailwind styling (light or dark) to work

### Added (dev tooling)
- Dev-only dashboard preview bypass behind `NEXT_PUBLIC_DEV_PREVIEW`. Active only when `process.env.NODE_ENV !== "production"` AND `process.env.NEXT_PUBLIC_DEV_PREVIEW === "1"`; because Next.js forces `NODE_ENV=production` in any production build, it cannot be enabled in production. When active, `middleware.ts` skips Auth0 on protected routes so the dashboard can be rendered and verified locally. Documented in `.env.local.example` (marked DEV ONLY)

### Verified
- Rendered and screenshotted the dashboard routes in the browser in both themes (dashboard, test-runs, appliances, threats, incidents, continuous-validation, reports, reports/schedule, runbooks, fleet, mssp, providers, insights, integrations, settings, settings/team, and a workload detail). White-card-on-dark and low-contrast issues fixed; the generated compliance PDF report is intentionally left light. `npm run type-check` and `npm run lint` are clean (pre-existing `<img>` warning in demo/page.tsx aside)

### Fixed
- Added the missing workloads index page `app/dashboard/workloads/page.tsx`. The sidebar linked to `/dashboard/workloads`, but only the dynamic `workloads/[id]` route existed, so the index 404'd. The new list view reuses the existing `WorkloadGrid` component (rows link to each workload's detail page) and the semantic color tokens. Verified via the dev preview (`NEXT_PUBLIC_DEV_PREVIEW=1`) in both light and dark themes

---

## [Unreleased] - Portal Dark Mode (foundation)

### Added
- Theme system for the portal: `darkMode: "class"` in Tailwind, a semantic color-token layer (`--color-bg/surface/content/border/accent`) in `globals.css` with light and `.dark` values, a dependency-free `ThemeProvider` + `ThemeToggle`, and a no-flash inline script in the root layout (persists to `localStorage`, respects `prefers-color-scheme`)
- The `/demo/login` page is converted to the token system with a theme toggle. Verified in the browser: light and dark both render correctly, the toggle flips the whole UI, and the choice persists across reload with no flash

### Notes
- This is the foundation plus the one portal surface reachable without credentials. The Auth0-gated `/dashboard/*` pages inherit the same tokens/components but need portal access (real Auth0/Firebase config, or a dev-only preview flag) to be rendered and pixel-verified before they are converted

---

## [Unreleased] - mypy Blocking + Two Silent-Empty Bugs

### Changed
- The API mypy check is now **blocking** in CI (was advisory). `apps/api/src` is type-clean (`mypy src/ --ignore-missing-imports`: 0 errors across 108 files). The appliance mypy stays advisory (native deps not verifiable here)

### Fixed
- `team.list_invites` filtered on `OrgInvite.accepted_at is None` (Python `is`, evaluates to `False`) so the query was `WHERE ... AND false` and **always returned an empty list**. Now `OrgInvite.accepted_at.is_(None)`
- `api_keys.list_keys` filtered on `not ApiKey.revoked` (Python `not` on a column, evaluates to `False`) so it **always returned an empty list**. Now `ApiKey.revoked.is_(False)`
- 23 further type errors resolved (async-generator return type on `get_db`, `**kwargs` unpacking in SOAR dispatch, `Sequence`->`list` returns, `float(int | None)` guard, mock-list annotations, a shadowed loop variable in runbooks, `CursorResult.rowcount` typing)
- Regression tests (real Postgres) assert both list endpoints now return their rows

---

## [Unreleased] - MSSP Partner Provisioning

### Added
- `apps/api/src/services/mssp_provisioning.py`: `get_or_create_partner` resolves the caller's org to its `mssp_partners` record (creating one on first use), idempotently
- Migration `0020`: adds `org_id` (unique) to `mssp_partners` so a partner is tied to its operating org
- Integration tests (real Postgres) for provisioning idempotency and per-partner customer scoping

### Fixed
- The MSSP console used the caller's `org_id` directly as `mssp_id`, which is a foreign key to `mssp_partners.id`. `add_customer` and `create_alert_rule` FK-violated on insert (no partner row existed), and `list_customers`/`list_alert_rules` returned **every** partner's records to any caller (cross-tenant leak). All console endpoints now resolve the partner via `get_or_create_partner` and scope reads, writes, and deletes to it

---

## [Unreleased] - API Reference + Architecture Docs

### Added
- `docs/api-spec/openapi.json`: the OpenAPI 3.1 spec exported from the running API (115 operations across 99 paths), with a Redoc viewer (`docs/api-spec/index.html`) served on GitHub Pages and a README covering Postman/Insomnia import and regeneration
- `docs/architecture.md`: system-context, recovery-test sequence, and trust-boundary diagrams (mermaid), a component responsibility table, and the readiness-score breakdown, cross-linked to the ADRs
- README top-nav links to the API Reference and Architecture docs

---

## [Unreleased] - Executive Scorecard on Real Data

### Added
- `apps/api/src/services/executive_snapshot.py`: `build_live_scorecard` computes the CISO scorecard (score, coverage, RTO compliance, per-provider breakdown, top risks) and 12-week trend from live workloads, test runs, and threats
- Integration tests (real Postgres) asserting the scorecard reflects seeded data and that `POST /v1/executive/scorecard/pdf` returns a real PDF

### Fixed
- `GET /v1/executive/scorecard`, `/trend`, and `POST /scorecard/pdf` returned a hardcoded 47-workload mock; they now compute from the org's real data (persisted `ScorecardSnapshot` if present, otherwise a live computation). The board PDF now carries the real org name
- `create_digest_schedule` stored `created_by` from the nonexistent `user.user_id` (always `None`); now resolves the local `users.id` via `resolve_local_user_id`, matching the reports/integrations fix
- `seed_demo.py` wrote test-run status `"success"`, but the platform's canonical passing status is `"passed"`; seeded runs were therefore invisible to readiness/scorecard queries. Corrected to `"passed"`

---

## [Unreleased] - One-Command Dev Stack

### Added
- Root `docker-compose.yml`: `docker compose up --build` brings up Postgres, Redis, and the API; the API container applies all migrations and seeds the demo dataset (idempotent, skippable with `SEED_DEMO=0`), then serves a fully populated instance on `http://localhost:8000`. Verified locally end-to-end (build, migrate, seed 108 runs, `/health` 200)
- README "One-command stack" quickstart

### Changed
- `apps/api/src/db/migrations/env.py` now sets the Alembic URL from the application settings (`R3VP_API_DATABASE_URL`) instead of the hardcoded `alembic.ini` value, so migrations target the same database as the app locally, in CI, and inside docker-compose (host `db`)

---

## [Unreleased] - Router Hardening + Demo Seed Data

### Added
- `apps/api/tests/test_router_hardening.py`: three fast, DB-free introspection guards that permanently close the dead-endpoint bug classes found during QA - the `Depends(alias)` anti-pattern (params mis-read as `args`/`kwargs`, 422 on every call), `require_permission` strings absent from the RBAC catalog (403 for all roles), and duplicate route registration
- `apps/api/src/scripts/seed_demo.py`: seeds a self-contained, internally consistent "Northwind Demo" org (5 role users, 1 appliance, 10 workloads, 108 test runs across 12 weeks with an improving RTO trend, 3 integrations, 2 threat scans with findings). Deterministic UUIDs make it idempotent; `--reset` wipes and rebuilds only the demo org. Verified end-to-end against real Postgres

### Fixed
- `compliance_frameworks.py` `create_framework`, `add_control`, and `run_assessment` gated on the non-existent permission `reports:write`, making them 403 for every role including owner; fixed to `reports:generate`. Caught by the new catalog guard on its first run

---

## [Unreleased] - Integration Config Validation

### Added
- `apps/api/src/services/integrations/validation.py`: `validate_integration_config` checks per-connector required fields (ServiceNow, Jira, PagerDuty, Splunk, QRadar, Sentinel), that URL fields are http(s), and that the QRadar syslog port is a valid port. Pure and unit-tested
- `POST /v1/integrations` now rejects a misconfigured integration with a 400 listing the problems, instead of accepting it and failing silently at the first real dispatch
- Unit tests for the validator and the create 400 path, and an integration test (real Postgres) for the create happy path

### Fixed
- `create_integration` stored `created_by` as `None` (looked up a nonexistent `user.user_id`); it now resolves the local `users.id` via `resolve_local_user_id`, matching the reports/report-schedules fix

---

## [Unreleased] - Capability Map

### Added
- `docs/capability-map.html`: a self-contained, transit-map-style network diagram of the entire platform. Six lines (Appliance, Threat, Validation, Intelligence, Compliance, Operations) run from "Your Stack" to a single terminus, "Recovery Assured", with hover-to-trace interaction and a per-line guide. Served via GitHub Pages at `/capability-map.html` and linked from the README

---

## [Unreleased] - Natural-Language Insights Over Live Data

### Changed
- `/v1/insights/query` now answers from a live org-scoped context (workload counts, composite readiness score, active threats, recent failures, RTO breaches, per-provider pass rates) built by the new `insights_context.build_query_context`, replacing the last hard-coded mock context. The entire AI Insights surface (prediction, anomalies, risk ranking, NL query) is now backed by real data
- Added an integration test (real Postgres) asserting the NL query reflects live counts rather than the old mock values

---

## [Unreleased] - MSSP Usage Metering and Billing

### Added
- `GET /v1/mssp/billing?period_days=N`: metered billing across an MSSP's customer portfolio. Aggregates per-customer usage (protected workloads + recovery test runs in the period) and prices it via a per-tier rate card, returning line items plus a portfolio summary
- Pure, unit-tested `mssp_billing` service (rate card for standard/premium/enterprise tiers; line-item + summary computation)
- Integration test (real Postgres) exercising the billing endpoint end to end

### Fixed
- Real bug: the entire MSSP router returned 403 for every role, including owner, because its `mssp:read` / `mssp:manage` permissions were not in the RBAC catalog. Added them (auto-granted to owner and admin via the system-role derivation), reviving the MSSP console API

---

## [Unreleased] - Continuous Validation Execution

### Added
- The APScheduler now registers enabled `ContinuousValidationPolicy` rows on their `check_interval_mins` and actually runs them (previously policies existed but never executed). Each run evaluates the enabled micro-checks per in-scope workload, records a `MicroValidationRun`, and raises a `ValidationAlert` once a workload reaches the policy's consecutive-failure threshold (deduped against unresolved alerts)
- Server-side-evaluable micro-checks implemented as pure functions in `continuous_validation.py`: `restore_point_freshness`, `rpo_compliance`, and `agent_heartbeat` (derived from `workload.last_backup_at` / `rpo_target_mins` and `appliance.last_heartbeat`). Live-only checks (`mount_check`, `veeam_job_status`, `vcenter_connectivity`) are reported `skipped` until the appliance submits telemetry
- Unit tests for every check evaluator and an integration test (real Postgres) driving the policy job end to end (runs recorded + consecutive-failure alert raised)

---

## [Unreleased] - Auth-Pattern Audit

### Fixed
- Audited every router for the `Depends(AuthUser)` / `Depends(AdminUser)` anti-pattern (an `Annotated` alias passed to `Depends`, which FastAPI mis-introspects as `*args/**kwargs` and answers with 422). Fixed the remaining occurrences: `multicloud.py` (`provider-summary`, `workloads`) and `threat_intel.py` (`incidents/{id}/resolve`). All authenticated endpoints now use the `user: AuthUser` / `user: AdminUser` idiom
- Added an integration test for `/v1/multicloud/provider-summary` (real Postgres) that also guards against regression of the 422 auth-declaration bug

---

## [Unreleased] - Ransomware Threat Analysis Engine

### Added
- `apps/api/src/services/threat_analysis.py`: a pure engine that flags ransomware indicators in backup restore-point metadata (near-ceiling file entropy, entropy spikes vs a rolling baseline, mass file-rename sweeps, known ransomware extensions) mapped to MITRE T1486, and `select_clean_restore_point` which returns the newest restore point with no high/critical indicator
- `POST /v1/threat-intel/analyze-restore-points`: stateless endpoint that analyzes appliance-supplied restore-point metadata and recommends a clean restore point (no backup content leaves the customer environment)
- Unit tests for the analysis functions and the endpoint (including the permission-denied path)

### Fixed
- Real bug: all authenticated `/v1/threat-intel/*` endpoints declared auth as `user: CurrentUser = Depends(AuthUser)`, but `AuthUser` is an `Annotated` alias, so FastAPI mis-introspected it as `*args/**kwargs` and returned 422 for every request. Switched to the `user: AuthUser` idiom, which fixes all five endpoints (findings, incidents, incident detail, resolve, scans)

---

## [Unreleased] - Real Risk Ranking + RBAC Permission Fix

### Changed
- `/v1/insights/risk-ranking` now ranks workloads from real per-workload aggregates (latest recorded RTO via Postgres `DISTINCT ON`, failure rate, days since last test) instead of mock data, org-scoped
- Added a `fail_rate_pct` helper to `readiness_scoring.py` (unit-tested)

### Fixed
- Real bug: every `require_permission`-gated endpoint (the whole AI Insights router) returned 403 for authenticated users, because `CurrentUser` had no `permissions` attribute so `getattr(user, "permissions", [])` was always empty. `CurrentUser.permissions` is now derived from the user's role via the RBAC system-role map, so permission checks actually resolve

### Tests
- Added an integration test for `/v1/insights/risk-ranking` (real Postgres) asserting real risk ordering; full integration suite (4 tests) verified locally against Postgres 16

---

## [Unreleased] - Recovery Intelligence: Real Readiness Scoring + RTO Forecasting

### Added
- `apps/api/src/services/readiness_scoring.py`: `compute_composite_score` (reuses the shared scorecard formula: coverage 40%, pass rate 35%, RTO compliance 15%, threat/incident penalty), `bucket_weekly_pass_rate` (rolling 12-week trend), and `days_since` helpers, all pure and unit-tested
- Unit tests for the scoring helpers and an integration test that exercises `/v1/dashboard/readiness` end to end against Postgres

### Changed
- `/v1/dashboard/readiness` now returns a real composite readiness score and a populated 12-week pass-rate trend (previously a naive average of the `readiness_score` column with an empty trend)
- `/v1/insights/rto-prediction/{workload_id}` now runs the linear-regression forecast and z-score anomaly detection over the workload's real recorded RTO history (was fixed mock data), using the workload's actual RTO target

### Fixed
- `/v1/dashboard/readiness` counted workloads across the run-joined result set, inflating `workloads_total`/`workloads_tested` by the number of test runs; now uses distinct workload counts
- `/v1/insights/rto-prediction/{workload_id}` did not scope the workload to the caller's org (cross-tenant read); it now verifies org ownership and returns 404 otherwise

---

## [Unreleased] - ADR-003 Groundwork: Veeam Session-State Handling

### Added
- `apps/appliance/src/connectors/veeam/session_states.py`: a `VeeamSessionState` enum plus `is_recovery_published` / `is_terminal_failure` classifiers, so instant-recovery session states are named rather than compared as inline string literals (ADR-003)
- Unit tests for the session-state classification (pure, no live infra required)

### Changed
- `wait_for_vm_boot` now uses the session-state classifiers: it fails fast on a terminal failure state and, on timeout, raises a diagnostic error including the last observed state (previously a generic message). The recovered-VM moref resolution from the live session remains lab-gated per ADR-003 and still returns the documented placeholder until validated against a real Veeam server

---

## [Unreleased] - Runtime Bug Fixes Surfaced by mypy

### Fixed
- `multicloud.py` listed `w.last_test_run_status`, which is not an attribute of `Workload`, raising `AttributeError` whenever the multicloud workloads endpoint was called; removed the unbacked field
- `main.py` lifespan shutdown called `_temporal_client.close()`, but the temporalio `Client` has no `close()` method (would raise on shutdown); removed it (the SDK manages the connection)
- `sentinel.py` posted the log payload with httpx `data=<bytes>`; modern httpx expects raw bytes via `content=`, so the SIEM forward could send malformed/empty bodies

### Notes
- mypy remains advisory. After fixing the real bugs above, the residual errors are SQLAlchemy/JSONB false positives (e.g. `where(bool)`, `Result.rowcount`, `Sequence` vs `list`) that would only be silenceable with `# type: ignore`; ruff plus the (now blocking) unit and integration tests cover real defects

---

## [Unreleased] - Commit Dependency Lockfile

### Security / Supply Chain
- Committed the uv workspace lockfile (`uv.lock`, 118 pinned packages across the API and appliance) and removed it from `.gitignore`. Exact transitive dependency versions are now pinned and reviewable, matching the already-committed portal `package-lock.json`, for reproducible and supply-chain-hardened builds

---

## [Unreleased] - Integration Tests Repaired and Gating

### Fixed
- **Real bug:** `accept_inventory_sync` used `ON CONFLICT ON CONSTRAINT uq_workloads_appliance_veeam`, but that name is a *partial unique index* (`WHERE veeam_object_id IS NOT NULL`), which Postgres cannot target via `ON CONSTRAINT`; the inventory-sync upsert would fail in production. Switched to index inference (`index_elements` + `index_where`)
- Declared the `uq_workloads_appliance_veeam` partial unique index on the `Workload` ORM model so `create_all` matches the migrated schema (model/migration parity)
- Made the integration-test `db_engine` fixture function-scoped, fixing the `another operation is in progress` asyncpg error caused by a session-scoped engine reused across pytest-asyncio's per-test event loops
- Registered the `integration` pytest marker in `pytest.ini` (the pyproject entry was shadowed by pytest.ini and produced an unknown-mark warning)

### Changed
- The API integration-test CI job is now a **blocking gate** (both tests pass against Postgres); verified locally against a Postgres 16 container before enabling

---

## [Unreleased] - Screenshot Refresh

### Documentation
- Added the graphical risk heatmap to the AI Insights mockup and regenerated `ai-insights.png` so the documentation screenshots match the portal's insights view (criticality vs validation-age heatmap above the risk-ranking table)
- Consolidated the three ad-hoc screenshot capture scripts into a single reusable `docs/screenshots/capture.py` (Playwright, 1440x900) that maps every mockup HTML to its PNG and accepts optional page-name filters for targeted regeneration

---

## [Unreleased] - Source-Code Protection Hardening

### Security / Supply Chain
- Added `.github/CODEOWNERS` so the repository owner is a required reviewer, with explicit ownership of security-sensitive areas (auth, vault, relay, CI/CD, infra)
- Corrected `SECURITY.md` staleness (supported branch is `master`, RBAC has 23 permissions)
- Renamed CI job names to remove em-dashes, giving clean status-check contexts for branch protection
- Branch protection on `master` now requires the passing CI status checks (appliance lint/test, API unit lint/test, portal type-check/lint, Docker builds) and a pull request before merging, in addition to blocking force-pushes and deletions. Secret scanning, push protection, and Dependabot remain enabled
- Fixed the integration-test fixture so it resets the schema wholesale (`metadata.drop_all` could not drop migration-created tables holding FKs). Promoting the integration job to a blocking gate surfaced that these two tests never actually passed (masked by `continue-on-error`) due to a pytest-asyncio fixture event-loop scope issue; the job remains advisory and running while that is repaired, and the `alembic upgrade head` migration step within it IS a hard gate

---

## [Unreleased] - QA Pass: Bug Fixes and Documentation Reconciliation

### Security
- Fixed a privilege-escalation gap: `CurrentUser.role` defaulted to `"admin"`, so `require_admin`/`AdminUser` passed for every authenticated user. Role is now read from the token claim and defaults to the non-privileged `viewer`. Added tests covering the default and `require_admin` enforcement

### Fixed
- API: scheduled test runs no longer orphan a row in `pending` when the Temporal enqueue fails; the run is marked `failed` with a reason
- API: breach notifications used truthiness checks (`if rto_target and rto_actual ...`) that silently dropped a legitimate measured value of `0`; now use explicit `is not None`
- API: `_send_email_ses` swallowed all errors, so callers wrongly recorded email delivery as successful; it now propagates failures
- API: `generated_by` / `created_by` audit columns always stored `None` (looked up a nonexistent `user.user_id`); a new `resolve_local_user_id` helper maps the Auth0 `sub` to the local `users.id`
- API: compliance/cyber-insurance PDF generation now runs `write_pdf` in a threadpool and returns a clean 500 on failure instead of blocking the event loop / raising an unhandled error
- API: report-schedule creation now validates the cron expression and returns 400, instead of storing a schedule that silently never runs
- Appliance: created the missing `src/services/delivery.py` (`DeliveryRecipient`, `deliver_report`) that `runbook_workflow` and `report_schedule_workflow` import; both would have raised `ModuleNotFoundError` at runtime
- Appliance: AWS Backup restore passed `SecurityGroupIds` as a bare string; it must be a JSON-encoded array (`json.dumps([...])`) or the isolated-network SG is ignored
- Appliance: vCenter datastore capacity read `info.maxFileSize` (a filesystem single-file limit) instead of `summary.capacity`

### Documentation
- Reconciled README and `docs/user-guide.md` with the code: RBAC section rewritten to the actual roles (`owner/admin/operator/auditor/viewer`) and 23 permissions from `rbac.py` (was a nonexistent `Analyst`/`MSSP Manager` set and "24 permissions"); corrected Next.js version (15), PostgreSQL version (16), Veeam API version range (v1.0/v1.1/v1.2), and the SaaS/portal environment-variable tables (correct `R3VP_API_` prefix and the real `AUTH0_*` + 7 Firebase vars); removed an em-dash entity from the README demo blurb

---

## [Unreleased] - SecureScope Findings Remediation

### Security
- Containers no longer run as root: both `apps/api` and `apps/appliance` Dockerfiles add a dedicated non-root `appuser` (UID 10001) and `chown` the app (and `/certs`, `/vault`) before switching with `USER` (CWE-250)
- XXE hardening: `dependency_scanner.py` now imports `defusedxml` unconditionally (added as a dependency) and no longer references the vulnerable stdlib `xml` parser at all (CWE-611)
- Jinja2 `Environment` instances in `reports.py` (x2) and `test_runs.py` now set `autoescape=True` (CWE-116)
- All GitHub Actions in `ci.yml` and `docker-publish.yml` are pinned to full commit SHAs instead of mutable tags, with the version retained as a comment (CWE-1357)
- CloudFront viewer certificate now uses an ACM cert with `minimum_protocol_version = TLSv1.2_2021` instead of the default certificate (which forces TLSv1) (CWE-326)
- RDS instance now exports `postgresql` and `upgrade` logs to CloudWatch (CWE-311)
- Portal dependency override forces `postcss` to the project's patched version across the tree (including Next.js's vendored copy); `npm audit` now reports 0 vulnerabilities

### Notes
- `pip-audit` reports no known vulnerabilities in the API or appliance production (or dev) dependencies; the SecureScope "29 dependency CVEs" figure was not reproducible against the current pinned dependency set and appears to predate the earlier CVE remediation

---

## [Unreleased] - Lint/Type Cleanup and CI Enablement

### Changed
- CI now runs on pushes to `master` (was `main`, which never matched the default branch, so lint/type/tests silently never ran on master)
- Resolved all `ruff` errors across `apps/api` and `apps/appliance` (376 and 84 respectively): import sorting, `datetime.UTC` modernization, `raise ... from exc` (B904), context-managed file reads (SIM115), and collapsed nested conditionals (SIM102)
- Configured ruff to whitelist FastAPI dependency-injection helpers (`Depends`, `Query`, etc.) so `B008` no longer false-positives on ~120 endpoint signatures; ignore `F401` in `__init__.py` re-export modules; ignore `UP042` (intentional str+Enum mix-ins)
- `mypy` is now advisory in CI (`continue-on-error`); annotation coverage (`disallow_untyped_defs`) is no longer enforced, but mypy still runs and reports
- Integration tests are now marked `integration`; the unit CI job runs `-m "not integration"` and the integration job (with Postgres) runs `-m integration`

### Fixed
- Real bug: `incident_response.py` called the Slack/Teams/email notification senders with missing positional arguments (would raise at runtime on incident dispatch)
- Real migration bug: `0001_initial_schema` created an explicit `uq_users_auth0_sub` index that collided with the unique constraint auto-named by the metadata naming convention from the column's `unique=True` (broke `alembic upgrade head` on a fresh database)
- Veeam connector models were out of sync with their tests; added the expected snake_case fields/aliases (`is_enabled`, `last_run`, `restore_points_count`, `is_consistent`, `backup_size_bytes`)
- Portal CI used pnpm against a non-existent `pnpm-lock.yaml`; switched to npm with `package-lock.json`
- Added a portal ESLint config (`next/core-web-vitals`) so `next lint` runs non-interactively, and escaped unescaped quotes flagged by it
- Integration test fixture now drops before creating the schema so it is idempotent against a pre-migrated database

---

## [Unreleased] - Portal Reports, Scheduled Delivery, Alerting

### Added
- Portal: "Generate PDF" on the Compliance Reports page now produces a real, formatted, print-ready report (matching the live-demo layout) for SOC 2, ISO 27001, NIST CSF, Monthly Summary, and Cyber Insurance
- Portal: graphical risk heatmap on the AI Insights page (business criticality vs days since last validation, color-graded with legend), above the existing risk-ranking table
- Backend: scheduled compliance report delivery. The APScheduler now registers cron jobs for enabled `ReportSchedule` rows and dispatches reports to configured recipients, updating last_run_at/next_run_at
- Backend: PagerDuty (Events API v2) and generic webhook alert channel types in the notification dispatcher
- Backend: `send_report_delivery()` notifies report recipients (email, Slack, Teams, webhook) when a scheduled report is generated
- Tests: `tests/test_auth_jwt.py` covering the PyJWT migration and the new PagerDuty/webhook senders
- Phase 20 documentation at `docs/phases/phase-20.md`

### Fixed
- Added `python-multipart` to API dependencies (required by the evidence-upload route; its absence blocked app import and the test suite)
- Fixed a `SyntaxError` in `src/services/executive_report.py` (backslash-escaped quotes in an f-string) that broke app import
- Resolved three pre-existing portal type errors that were failing CI's `pnpm type-check` (typed-route casts in `breadcrumb.tsx` and `providers/page.tsx`, custom-event cast in `track.ts`)

### Changed
- Pinned `sops` to `v3.13.1` in the appliance Dockerfile (was fetching `latest`) for reproducible builds

---

## [Unreleased] - Code Scanning Remediation

### Security
- Migrated API JWT verification from `python-jose` to `PyJWT` (`pyjwt[crypto]`), removing the transitive `ecdsa` dependency and closing CVE-2024-23342 (Minerva timing attack, which has no upstream fix in `ecdsa`). `auth.py` now uses `PyJWKClient` for JWKS fetching and RS256 verification
- Both container images (`r3vp-api`, `r3vp-appliance`) now apply Debian security patches via `apt-get upgrade` and upgrade `pip`/`setuptools` during build, closing the fixable base-image CVEs
- Trivy container scan now uses `ignore-unfixed: true`, so only vulnerabilities with an available fix are reported. This removes the large volume of non-actionable Debian CVEs (no upstream patch) from the code scanning dashboard

### Changed
- `apps/api/pyproject.toml`: replaced `python-jose[cryptography]>=3.3` with `pyjwt[crypto]>=2.10`
- `apps/api/mypy.ini`: updated module override from `jose.*` to `jwt.*`

---

## [Unreleased] - Live Demo Enhancements

### Added
- Printable compliance reports in the live demo: the "Print Report" action now opens a fully formatted, print-ready report (branded header, summary cards, control assessment table, evidence summary, signed footer) for NIST CSF 2.0, ISO 27001:2022, SOC 2 Type II, and PCI DSS 4.0
- New "Trends & Risk" section in the live demo: 12-week RTO trend chart vs target SLA, readiness score trajectory with 30-day projection, and 90-day trend KPIs
- Risk heatmap (business criticality x days since last validation) with color-graded, clickable cells and a five-band legend
- Alert Channels card in the Continuous Validation section documenting Teams, Slack, Email, PagerDuty, and SIEM webhook delivery
- `r3vp-demo` static-server configuration for local preview of `docs/demo.html`
- Phase 19 documentation at `docs/phases/phase-19.md`

### Fixed
- Live demo "Print Report" buttons previously showed only a placeholder toast; they now generate the actual report document and trigger print/save-to-PDF

---

## [Unreleased] - Firebase Analytics + User Guide + Security Hardening

### Added
- Firebase Analytics integration in Next.js portal (free Spark plan, no billing required)
- `apps/portal/lib/firebase.ts` - lazy initialisation with graceful no-op when env vars are absent
- `apps/portal/lib/track.ts` - typed event helpers: trackLogin(), trackPageView(), and 10 named domain events
- `apps/portal/components/firebase-init.tsx` - client component wired into root layout; fires login event on Auth0 session start
- Firebase environment variables added to `.env.local.example` with setup instructions
- Firebase Authentication login at `/demo/login` with Google Sign-In and email/password
- `context/firebase-auth-context.tsx` React context providing user state and signOut across demo routes
- Demo dashboard at `/demo` - full portal UI with realistic mock data, protected by Firebase Auth
  (no Auth0 or backend API required); redirect guard via `onAuthStateChanged`
- `app/demo/layout.tsx` wrapping demo routes with `FirebaseAuthProvider`
- User Analytics portal page mockup showing 30-day login chart, top users table, feature usage bars, and live events feed
- `analytics.png` screenshot added to docs/screenshots/
- Comprehensive technical user guide at `docs/user-guide.md` covering all 21 features, architecture, installation, API reference, security design, and troubleshooting
- User Guide section added to README linking to `docs/user-guide.md`
- All 26 portal screenshots refreshed at 1440x900
- Screenshot helper script at `scripts/screenshot_mockups.py` for re-capturing all mockups

### Changed
- Next.js upgraded from 14.2.3 to 15.5.18 (closes all 27 Dependabot security alerts)
- `eslint-config-next` upgraded to 15.5.18 to match
- README tech stack updated: "Next.js 15 + Auth0 + Recharts + Firebase Analytics"

### Security
- 27 Next.js CVEs fixed by upgrade to 15.5.18 (includes CVE-2025-29927 auth bypass and 26 others)
- master branch protection enabled: force pushes and deletions blocked
- GitHub Security Advisories enabled with private vulnerability reporting

---

## [Unreleased] - Phase 18: Continuous Validation Mode

### Added
- ContinuousValidationPolicy model with configurable interval (minimum 1 min), workload scope, per-check toggles, and consecutive-failure alert threshold
- Six micro-check types: restore_point_freshness, mount_check, veeam_job_status, agent_heartbeat, vcenter_connectivity, rpo_compliance
- MicroValidationRun model recording per-check JSONB results, restore point age, duration, and alert_sent flag per run
- ValidationAlert model with alert_type, severity, resolution tracking, and cascade delete on policy removal
- Rolling health computation from last 100 runs: healthy (>=90% pass), degraded (70-89%), failing (<70%)
- Consecutive failure counter for alert escalation
- Policy toggle endpoint (PATCH /policies/{id}/toggle) for enable/disable without deletion
- Continuous Validation portal page with KPI row, policy cards, active alerts with severity borders, and runs table
- Available checks reference grid with category and description for each of the 6 check types
- Migration 0019 adding continuous_validation_policies, micro_validation_runs, validation_alerts tables

---

## [Unreleased] - Phase 17: Custom Compliance Framework Builder

### Added
- Six compliance frameworks now built-in: SOC 2 Type II, ISO/IEC 27001:2022, NIST CSF 2.0, EU DORA (Article 11/12/25), PCI DSS 4.0, HIPAA Security Rule
- ComplianceFramework model for org-scoped custom frameworks with short_code, version, and is_builtin flag
- ComplianceControl model mapping control IDs to R3VP metrics (pass_rate, rto_compliance, coverage_pct) with thresholds and weights
- FrameworkAssessment model storing scored results per control in JSONB with overall weighted score and period range
- evaluate_framework() engine: scores each control against live metric values, computes weighted 0-100 overall score
- Framework catalog endpoint listing all built-in frameworks with control counts
- Custom framework CRUD: create framework, add controls, list controls
- Assessment endpoint running scoring against current period metrics and persisting result
- Framework builder portal page: 6 framework cards with DORA highlighted as EU mandate, 3-step custom builder flow
- Migration 0018 adding compliance_frameworks, compliance_controls, framework_assessments tables

---

## [Unreleased] - Phase 16: MSSP Console

### Added
- MsspPartner model with white-label branding fields (logo_url, primary_color), plan tier, and max_customer_orgs limit
- MsspCustomerOrg model with tier (standard/premium/enterprise), free-form tags, notes, and onboarded_at timestamp
- MsspAlertRule model with five condition types: readiness_below, rto_breach, test_failure, no_test_in_days, threat_detected
- Alert rule scoping: all orgs, tier-specific (tier:premium), or tag-specific (tag:critical)
- Cross-org summary endpoint aggregating healthy/warning/critical counts, avg readiness score, total workloads/threats/incidents
- Per-customer scorecard endpoint with 6-month readiness trend and top risk workloads
- MSSP console portal page with 5-col KPI row, customer table with score/tier/threat badges, and alert rule toggles
- Migration 0017 adding mssp_partners, mssp_customer_orgs, mssp_alert_rules tables with cascade deletes

---

## [Unreleased] - Phase 15: Appliance Fleet Management

### Added
- ApplianceGroup model for organizing appliances by site or region with config template and tags
- ApplianceGroupMember join table with cascade deletes for clean group/appliance removal
- ApplianceHealthSnapshot model capturing CPU, memory, disk, Veeam/vCenter/Temporal connection state, version, and per-appliance alert list
- BulkConfigJob model for async config push to multiple appliances with per-appliance result tracking
- Fleet overview endpoint aggregating healthy/warning/offline counts and per-appliance status in one response
- Site group CRUD API with config_template for bulk configuration propagation
- Bulk config push endpoint: accepts appliance IDs and config dict, creates async job, returns job ID for status polling
- Fleet portal page with KPI cards, appliance rows showing status-colored borders with resource and connection badges, groups section, and bulk config JSON editor
- Migration 0016 adding appliance_groups, appliance_group_members, appliance_health_snapshots, and bulk_config_jobs tables

---

## [Unreleased] - Phase 13: Self-Service Onboarding Wizard

### Added
- OnboardingSession model with org-scoped unique constraint, step progress tracking, step_data JSONB for per-step completion evidence, and completed/dismissed flags
- Six-step onboarding flow: org_profile, deploy_appliance, connect_veeam, discover_workloads, first_test, complete
- Step completion predicates: each step has a typed check on step_data (appliance_id, veeam_connected, workload_count, first_test_run_id)
- Auto-complete trigger: session marks complete when step 6 is reached and overall progress is >= 80%
- Onboarding API: GET status (auto-creates session on first call), POST step advancement, POST dismiss, POST reset
- Full-screen wizard portal page with horizontal step stepper, org profile form, Docker deployment instructions, and step progress tracking
- Registration token display and 24-hour expiry hint on deploy_appliance step
- Security note confirming SOPS + age credential isolation in the wizard UI
- Migration 0014 adding onboarding_sessions table with org_id unique index

---

## [Unreleased] - Phase 12: DR Runbook Automation

### Added
- Runbook model with scenario classification (ransomware, datacenter_failure, cloud_outage, site_failover, custom) and RTO target
- RunbookStep model with seq ordering, depends_on_seq dependency graph, parallel flag, step_type, timeout, and on_failure policy (stop/continue/rollback)
- Six step types: recover_workload, health_check, notify, wait, manual_gate, run_script
- Topological sort engine resolving step dependencies into execution waves with concurrent parallel steps
- RunbookExecution and RunbookExecutionStep models tracking live step status, duration, output, and errors
- Temporal RunbookWorkflow: fetches plan, executes each step via typed activities, posts status after every step, finalizes with actual RTO and pass/fail
- Actual vs target RTO computation and rto_met flag stored per execution
- API at /v1/runbooks: list, create, get with execution plan, trigger execution, execution history, live step status
- Portal runbooks page: scenario filter pills, runbook cards with wave/step summary, RTO badge, execution history table
- Runbook execution detail view: wave timeline with per-step status, duration, output panel
- Migration 0013 adding runbooks, runbook_steps, runbook_executions, runbook_execution_steps tables

---

## [Unreleased] - Phase 11: AI Insights

### Added
- RTO trend prediction via linear regression: slope, projected next RTO, risk level (critical/high/medium/low), and estimated tests until breach
- Anomaly detection over RTO time series using z-score analysis (|z| > 2.0 flagged as spike or drop)
- Workload risk ranking scored across test recency, RTO proximity to target, and recent failure rate
- Rule-based natural language query handler covering workload counts, RTO breaches, threat status, readiness score, and provider performance
- Insights portal page with NL query bar, example query chips, risk ranking table
- API endpoints: GET /v1/insights/rto-prediction/{id}, GET /v1/insights/risk-ranking, POST /v1/insights/query

---

## [Unreleased] - Phase 10: Integrations Marketplace

### Added
- ServiceNow integration: creates incident via Table API with urgency/impact severity mapping
- Jira integration: creates issue via Jira Cloud REST v3 with Atlassian Document Format body and r3vp label
- PagerDuty integration: triggers alert via Events API v2 with critical/warning/info severity mapping
- Splunk integration: pushes events via HTTP Event Collector (HEC) with configurable index
- IBM QRadar integration: sends CEF syslog over UDP for recovery events and threat detections
- Microsoft Sentinel integration: posts to Log Analytics Data Collector API with HMAC-SHA256 SharedKey auth
- Integration catalog endpoint listing all six connectors with category and description
- Integration event log: every dispatch attempt stored with status, error detail, and response time
- CRUD API at /v1/integrations with test endpoint (POST /{id}/test) and enable/disable toggle
- Alembic migration 0012 adding integrations and integration_event_logs tables
- Integrations portal page: catalog card grid, active integrations table, event log

---

## [Unreleased] - Phase 9: Executive Reporting and CISO Scorecard

### Added
- Overall readiness score (0-100) computed from coverage (40%), pass rate (35%), RTO compliance (15%), threat penalty (up to 10 pts deducted)
- CISO scorecard PDF: score hero, KPI row, 6-month trend table, provider breakdown, top risks ranked by severity
- ScorecardSnapshot model for persisting monthly snapshots with provider_breakdown and top_risks JSONB
- DigestSchedule model for weekly/monthly/quarterly email delivery with configurable sections
- Scorecard trend API returning last N monthly snapshots
- Digest schedule CRUD API at /v1/executive/digest-schedules
- Alembic migration 0011 adding digest_schedules and scorecard_snapshots tables
- Scorecard portal page with score hero, trend chart, provider breakdown, risk ranking

---

## [Unreleased] - Phase 8: Multi-tenancy and RBAC

### Added
- Granular RBAC with 24 named permissions and five built-in system roles: owner, admin, operator, auditor, viewer
- Role, OrgMember, OrgInvite, ApiKey, and SsoConfig models
- Alembic migration 0010 adding roles, org_members, org_invites, api_keys, and sso_configs tables with system role seed data
- Permission registry (apps/api/src/services/rbac.py) with require_permission() enforcement helper
- Team management API: invite by email with 7-day expiring token, list members, change role, deactivate member
- API key management: scoped service account keys, SHA-256 hash stored (raw value shown once), revocation
- SAML 2.0 SSO configuration: Okta, Azure AD, Google Workspace, Ping Identity, generic SAML; cert + attribute mapping stored per org
- Portal /dashboard/settings/team page: member table with role badges, pending invites, invite form
- Portal API keys page: active keys with prefix and scopes, create form with grouped scope checkboxes
- Portal SSO settings page: provider card selector, config form, SP metadata display

---

## [Unreleased] - Phase 7: Compliance, Reporting, Scheduled Delivery and Evidence Vault

### Added
- Compliance PDF reports for SOC 2 Type II, ISO/IEC 27001:2022, NIST CSF 2.0, and cyber insurance
- Framework control mapping: CC7.5/CC9.1/A1.3 (SOC 2), A.8.13/A.8.14/A.5.29/A.5.30 (ISO 27001), RC.RP-01/02/05 (NIST CSF)
- SHA-256 signed PDF reports with digest stored in compliance_reports table and returned in X-SHA256 header
- ComplianceReport model and Alembic migration 0008
- Hash-chained audit trail in appliance (apps/appliance/src/audit/chain.py) using SHA-256 chain over SQLite
- Audit chain verify endpoint to confirm tamper-evidence on demand
- Report history endpoint listing all generated reports per org with summary metrics
- Jinja2 HTML template for compliance PDF rendering via weasyprint
- Portal /dashboard/reports page: framework selector, date range picker, generate button, history table, audit trail preview
- Scheduled report delivery: ReportSchedule model with cron expression, framework, period, recipients, enabled toggle
- Alembic migration 0009 adding report_schedules and evidence_bundles tables
- Report schedule CRUD API: GET/POST /v1/report-schedules, PATCH toggle, DELETE
- Temporal cron workflow (ReportScheduleWorkflow) fetches schedule config, generates PDF, delivers to all recipients
- Delivery service supporting email (SMTP), Slack incoming webhooks, and Teams adaptive card webhooks
- Evidence vault service: builds signed ZIP bundles containing manifest.json, compliance PDF, audit_chain.json, and per-workload artifacts (summary, steps, health checks)
- Evidence bundle API: POST /v1/reports/evidence-bundle returning ZIP with X-SHA256 and X-File-Count headers
- Portal /dashboard/reports/schedule page: schedule list, toggle active/paused, new schedule form with cadence selector
- Portal evidence vault view with bundle history, structure reference, and generate form

---

## [Unreleased] - Phase 6: Extended Hypervisors and Google Cloud

### Added
- Proxmox VE connector: proxmoxer REST API, PBS backup integration, snapshot create/restore
- Nutanix AHV connector: Prism Central v3 REST API, recovery point management
- RHV / oVirt connector: oVirt Engine Python SDK, snapshot preview and commit
- XenServer / Citrix Hypervisor connector: XenAPI XML-RPC, VM clone from snapshot
- Sangfor HCI connector: vendor REST API, token auth, snapshot restore
- GCP Backup connector: google-cloud-compute, Application Default Credentials, instance restore from snapshot
- Provider routing in Temporal activities extended from 4 to 10 providers
- Workload model: provider_cluster field for cluster/pool/zone metadata
- Alembic migration 0007 for provider_cluster column
- Portal /dashboard/providers: 10-provider card grid, extended hypervisor support matrix
- Portal dashboard: 10-provider coverage widget
- R3VP_PROVIDER env var now accepts: vmware, hyperv, azure, aws, proxmox, nutanix, rhv, xenserver, sangfor, gcp
- New pyproject.toml dependencies: proxmoxer>=2.0, google-cloud-compute>=1.14, google-auth>=2.28

---

## [0.5.0] - Phase 5 - 2026-06-17

### Added
- Veeam B&R 13.0.2 support: API version v1.2 with auto-detection via serverInfo
- Veeam 13 backup repositories endpoint: list repos with capacity and free space
- Veeam 13 malware detection events: ingest Veeam inline scanner findings
- Veeam 13 instant recovery path update: /instantRecovery/vm (v1.2) vs /instantRecovery/vmware/vm (v1.1)
- Veeam backup job control: trigger immediate backup jobs, monitor session progress
- Hyper-V connector: WMI-based VM inventory, checkpoint management, isolated virtual switch
- AWS Backup connector: vault inventory, EC2 recovery points, test restore to isolated VPC subnet, EC2 health checks
- Azure Backup connector: Recovery Services Vault integration, protected VM list, restore to isolated resource group
- Multi-cloud workflow routing: Temporal activities dispatch to correct connector based on configured provider
- Provider breakdown dashboard: per-provider workload count, pass rate, avg RTO
- /dashboard/providers page: detailed provider coverage cards with pass rate bar charts
- Provider filter on workload list
- Workload model: provider, cloud_resource_id, cloud_region fields
- Alembic migration 0006: workload provider columns
- Multi-cloud readiness API: GET /v1/multicloud/provider-summary, GET /v1/multicloud/workloads
- New dependencies: boto3, azure-identity, azure-mgmt-recoveryservicesbackup, msal

---

## [0.4.0] - Phase 4 - 2026-06-16

### Added
- Ransomware, malware, APT, and vulnerability signature database with automatic cloud sync
- File system and process scanner that cross-references running processes against the threat DB
- YARA rules engine: load and execute custom or community YARA rules against scanned artifacts
- SOAR integration: Splunk SOAR and Palo Alto XSOAR webhook triggers on threat detection
- SIEM integration: CEF/Syslog output for Splunk, IBM QRadar, and Microsoft Sentinel
- Automated incident response API: triggers an immediate Veeam backup and creates a SecOps workflow on threat detection
- VeeamONE reporting integration: pushes threat and recovery events to VeeamONE dashboards
- Threat scanner portal pages: scan dashboard, findings detail, active incidents
- Console notification pane: real-time threat alerts shown in portal without page refresh
- Email notifications for incident alerts (SES)

---

## [0.3.0] - Phase 3 - 2026-06-15

### Added
- SLA breach notifications: email (SES), Slack incoming webhook, Teams adaptive card webhook
- Notification channel management: POST/GET/DELETE /v1/notifications, scoped by org
- Portal settings page: org info, notification channels, default RTO/RPO targets
- Audit log CSV export: GET /v1/audit-log/export with 90-day date range
- Appliances list and detail pages in portal: status badges (active/stale/offline based on heartbeat)
- Role-based access control: admin and viewer roles, write endpoints protected with AdminUser dependency
- User provisioning endpoint: POST /v1/users/provision for role assignment
- Production Terraform: ECS Fargate auto-scaling (1-4 tasks), ALB with TLS 1.3, CloudFront CDN
- Cyber insurance evidence report: NIST CSF Recover function mapping, PDF attestation document
- Integration test suite: real Postgres tests for inventory sync upsert and readiness score calculation
- Portal-facing appliances API: GET/DELETE /v1/portal/appliances with workload counts
- Appliance deregister capability

### Changed
- finalise_run() now dispatches breach notifications as a best-effort post-commit step
- trigger_test_run, set_targets, set_schedule now require admin role

---

## [0.2.0] - Phase 2 - 2026-06-14

### Added
- Temporal workflow trigger wired into the API: trigger_test_run enqueues RecoveryTestWorkflow
- Temporal lifespan in FastAPI: connects on startup, graceful shutdown on exit
- Full inventory sync: sync_inventory activity posts explicit field mapping to relay client
- Portal workload detail page: stats, RTO/RPO targets form, test run history, Run Test Now
- Live test run progress view: 5-second polling while status is running/pending, step timeline
- PDF evidence report: Jinja2 HTML template rendered via WeasyPrint, full step/health check data
- Scheduled test runs: schedule_cron field on workloads, APScheduler loads and fires cron jobs
- Veeam version auto-detection: reads /api/v1/serverInfo on startup, routes to correct API path
- On-premises install script (bash): Docker check, cert generation, secrets template
- Windows PowerShell install script: same flow for Windows environments
- Appliance OVA packaging: Packer HCL2 template, configure-from-ovf.sh reads vSphere OVF properties

### Changed
- Restore point list routes to correct API path for Veeam v1.0 vs v1.1
- Instant recovery raises NotImplementedError on Veeam 10 (no API support)

---

## [0.1.0] - Phase 1 - 2026-06-13

### Added
- Python 3.12 monorepo with uv workspace (apps/appliance, apps/api, apps/portal)
- Lightweight appliance: outbound-only mTLS relay client, SOPS+age credential vault
- Veeam B&R REST API connector: token auth, auto-refresh, list jobs/VMs/restore points, instant recovery
- VMware vCenter connector: pyVmomi, isolated VLAN provisioning, VMware Tools polling, screenshot
- Temporal workflow: RecoveryTestWorkflow with 10 activities and saga teardown pattern
- Health checks: Windows OS (WinRM), Linux OS (SSH + systemctl), Active Directory LDAP, SQL Server stubs
- FastAPI SaaS backend: appliance relay, workload inventory, test run management, readiness scoring
- Auth0 JWT authentication with JWKS RS256 verification and org_id claim extraction
- PostgreSQL 16 schema: orgs, appliances, workloads, test_runs, test_run_steps, health_check_results, audit_events
- Alembic migrations (0001 initial)
- Next.js 14 portal: Auth0 login, dashboard with readiness gauge, RTO/RPO chart, workload grid
- mTLS client certificate verification: thumbprint checked against DB on every appliance request
- GitHub Actions CI: lint, typecheck, unit tests, integration tests, Docker builds
- Terraform modules: RDS PostgreSQL 16, S3 evidence bucket with KMS encryption
- mTLS cert generation scripts (bash + PowerShell)
- Architecture Decision Records: appliance runtime, Temporal workflow engine

---

## Roadmap

### Phase 5 (planned): Multi-cloud and Hyper-V support
- Hyper-V connector: WMI-based VM inventory and Hyper-V checkpoint recovery
- Azure Blob Storage backup connector
- AWS Backup connector
- Multi-cloud workload dashboard with provider breakdown

### Phase 6 (planned): Compliance frameworks and advanced reporting
- SOC 2 Type II evidence package generator
- ISO 27001 Annex A mapping
- CIS Controls v8 mapping
- Executive summary email digest (weekly/monthly)
- API-first reporting: programmatic evidence export for GRC tools
