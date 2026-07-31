# Dependency License Review

**This document is a technical inventory, not legal advice, and it does not
state that the project is legally compliant.** It records the direct
dependencies declared in the project manifests, their commonly published
licenses, and items that may warrant legal review before or after the move to
AGPL-3.0 plus a commercial license. Licenses below are as commonly published by
each project and were compiled manually from the manifests; they were not
produced by an automated license scanner and exact per-version and transitive
license terms should be verified with a dedicated tool (for example
`pip-licenses`, `uv pip licenses`, or `license-checker`).

Scope: direct dependencies only, from `apps/api/pyproject.toml`,
`apps/appliance/pyproject.toml`, the root `pyproject.toml` dev dependencies, and
`apps/portal/package.json`. Transitive dependencies are not enumerated here.

## Direct production dependencies (Python - API)

| Package | Commonly published license |
|---|---|
| fastapi | MIT |
| python-multipart | Apache-2.0 |
| uvicorn[standard] | BSD-3-Clause |
| sqlalchemy[asyncio] | MIT |
| alembic | MIT |
| asyncpg | Apache-2.0 |
| pydantic | MIT |
| pydantic-settings | MIT |
| temporalio | MIT |
| pyjwt[crypto] | MIT |
| boto3 | Apache-2.0 |
| structlog | MIT / Apache-2.0 (dual) |
| redis | MIT |
| httpx | BSD-3-Clause |
| weasyprint | BSD-3-Clause |
| jinja2 | BSD-3-Clause |
| apscheduler | MIT |
| aiofiles | Apache-2.0 |
| setuptools | MIT |
| msgpack | Apache-2.0 |

## Direct production dependencies (Python - Appliance)

| Package | Commonly published license |
|---|---|
| httpx[http2] | BSD-3-Clause |
| pyvmomi | Apache-2.0 |
| temporalio | MIT |
| cryptography | Apache-2.0 OR BSD-3-Clause (dual) |
| pydantic | MIT |
| pydantic-settings | MIT |
| structlog | MIT / Apache-2.0 (dual) |
| tenacity | Apache-2.0 |
| paramiko | **LGPL-2.1** (weak copyleft) |
| pywinrm | MIT |
| pillow | MIT-CMU / HPND (permissive) |
| yara-python | Apache-2.0 / BSD-3-Clause |
| psutil | BSD-3-Clause |
| boto3 | Apache-2.0 |
| azure-identity | MIT |
| azure-mgmt-recoveryservicesbackup | MIT |
| msal | MIT |
| proxmoxer | MIT |
| requests | Apache-2.0 |
| google-cloud-compute | Apache-2.0 |
| google-auth | Apache-2.0 |
| defusedxml | PSF-2.0 (Python Software Foundation) |
| setuptools | MIT |
| msgpack | Apache-2.0 |

## Direct development dependencies

| Package | Ecosystem | Commonly published license |
|---|---|---|
| pytest | pip | MIT |
| pytest-asyncio | pip | Apache-2.0 |
| httpx | pip | BSD-3-Clause |
| ruff | pip | MIT |
| mypy | pip | MIT |
| @types/node, @types/react, @types/react-dom | npm | MIT |
| autoprefixer | npm | MIT |
| eslint | npm | MIT |
| eslint-config-next | npm | MIT |
| postcss | npm | MIT |
| tailwindcss | npm | MIT |
| typescript | npm | Apache-2.0 |

## Direct production dependencies (Portal - npm)

| Package | Commonly published license |
|---|---|
| @auth0/nextjs-auth0 | MIT |
| @radix-ui/react-dialog, -dropdown-menu, -progress, -select, -tabs, -tooltip | MIT |
| @tanstack/react-query | MIT |
| axios | MIT |
| clsx | MIT |
| date-fns | MIT |
| firebase | Apache-2.0 |
| lucide-react | ISC |
| next | MIT |
| react, react-dom | MIT |
| recharts | MIT |
| tailwind-merge | MIT |
| zustand | MIT |

npm overrides in place for security patching: `undici`, `postcss`, `sharp`,
`brace-expansion` (see `apps/portal/package.json`).

## Dependencies with strong copyleft, source-available, non-commercial, custom, or potentially incompatible terms

- **paramiko - LGPL-2.1 (weak / library copyleft).** Used as an unmodified
  library dependency. LGPL library use inside a larger work is generally
  handled differently from strong copyleft, but the interaction of LGPL-2.1
  library use with an AGPL-3.0 and a separate proprietary commercial
  distribution should be reviewed, especially for the commercial-license path
  and for any static-linking or vendoring scenario.
- No dependency in the direct set is published under a non-commercial-only or a
  bespoke source-available license based on this inventory.

## Dependencies with missing or unknown licenses

- None identified as missing in the direct set from the manifests. Some
  packages publish dual or compound licenses (noted above). Exact SPDX
  identifiers per pinned version were not machine-verified.

## Files or code that appear copied or vendored from third parties

- No third-party source code appears copied or vendored directly into this
  repository's tree; all third-party code is consumed through the package
  managers (uv / npm) and their lock files (`uv.lock`,
  `apps/portal/package-lock.json`).
- `docs/api-spec/index.html` loads Redoc from a CDN at view time; the Redoc
  library is not vendored into the repository.

## Items requiring legal review

1. The AGPL-3.0 relicensing itself, and the dual-license (AGPL + commercial)
   structure, including the ability to offer a proprietary commercial license
   while depending on the packages above.
2. **paramiko (LGPL-2.1)** interaction with both the AGPL-3.0 path and the
   proprietary commercial path.
3. Confirmation, with an automated scanner, of transitive dependency licenses
   and exact per-version terms (this document covers direct dependencies only).
4. Compatibility of each dependency's license with distribution under both the
   AGPL-3.0 and a separate commercial license.
