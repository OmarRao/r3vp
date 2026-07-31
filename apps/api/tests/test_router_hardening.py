# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Router hardening guards.

These tests permanently close the two dead-endpoint bug classes found during
the QA pass:

1. `Depends(AuthUser)` / `Depends(AdminUser)` - passing an `Annotated` alias to
   `Depends()` makes FastAPI mis-introspect the dependency as `*args/**kwargs`,
   so the endpoint 422s on every request. The correct idiom is `user: AuthUser`.
2. A `require_permission(...)` call referencing a permission string that is not
   in the RBAC catalog - no role can ever hold it, so the endpoint 403s for
   everyone (including owner).

Both are static/introspection checks: fast, no database required.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.routing import APIRoute

from src.main import app
from src.services.rbac import PERMISSIONS

ROUTERS_DIR = Path(__file__).resolve().parent.parent / "src" / "routers"


def test_no_depends_alias_antipattern():
    """No route should expose synthetic `args`/`kwargs` params, which is how the
    `Depends(AuthUser)` misread manifests in FastAPI's dependant."""
    offenders = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            names = {p.name for p in route.dependant.query_params}
            if names & {"args", "kwargs"}:
                offenders.append(f"{sorted(route.methods)} {route.path}")
    assert not offenders, (
        "Endpoints with the Depends(alias) anti-pattern (params became "
        f"args/kwargs -> 422): {offenders}"
    )


def test_router_permission_strings_are_in_catalog():
    """Every permission string passed to require_permission must exist in the
    RBAC catalog, or the endpoint is unreachable for all roles."""
    pat = re.compile(r"""require_permission\(.*?,\s*["']([a-z_]+:[a-z_]+)["']\)""", re.DOTALL)
    missing: dict[str, set[str]] = {}
    for f in ROUTERS_DIR.glob("*.py"):
        for perm in pat.findall(f.read_text(encoding="utf-8")):
            if perm not in PERMISSIONS:
                missing.setdefault(f.name, set()).add(perm)
    assert not missing, f"Permission strings not in the RBAC catalog: {missing}"


def test_app_has_no_duplicate_routes():
    """Guards against a router being registered twice under the same path."""
    seen: dict[tuple, int] = {}
    for route in app.routes:
        if isinstance(route, APIRoute):
            for method in route.methods:
                seen[(method, route.path)] = seen.get((method, route.path), 0) + 1
    dupes = [k for k, n in seen.items() if n > 1]
    assert not dupes, f"Duplicate (method, path) routes registered: {dupes}"
