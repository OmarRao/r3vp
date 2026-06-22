"""Permission definitions and enforcement helpers."""
from __future__ import annotations

PERMISSIONS = {
    # Workloads
    "workloads:read":     "View workloads and their status",
    "workloads:write":    "Create and update workload configuration",
    "workloads:delete":   "Remove workloads",
    # Test runs
    "test_runs:read":     "View test run results",
    "test_runs:trigger":  "Trigger a test run",
    # Reports
    "reports:read":       "View and download compliance reports",
    "reports:generate":   "Generate new compliance PDFs",
    "reports:schedule":   "Create and manage scheduled delivery",
    # Evidence
    "evidence:read":      "Download evidence bundles",
    # Threats
    "threats:read":       "View threat scanner findings",
    "incidents:read":     "View incidents",
    "incidents:write":    "Acknowledge and resolve incidents",
    # Audit
    "audit:read":         "View and export audit log",
    # Team management
    "team:read":          "View team members",
    "team:invite":        "Invite users to the org",
    "team:manage":        "Change member roles and remove members",
    # API keys
    "api_keys:read":      "View API keys",
    "api_keys:write":     "Create and revoke API keys",
    # Appliances
    "appliances:read":    "View appliances",
    "appliances:manage":  "Register and deregister appliances",
    # Settings
    "settings:read":      "View org settings",
    "settings:write":     "Update org settings and notification channels",
    # SSO
    "sso:manage":         "Configure SAML SSO",
}

SYSTEM_ROLES: dict[str, list[str]] = {
    "owner": list(PERMISSIONS.keys()),
    "admin": [p for p in PERMISSIONS if p != "sso:manage"],
    "operator": [
        "workloads:read", "workloads:write",
        "test_runs:read", "test_runs:trigger",
        "reports:read", "evidence:read",
        "threats:read", "incidents:read", "incidents:write",
        "audit:read", "appliances:read", "appliances:manage",
        "team:read", "settings:read",
    ],
    "auditor": [
        "workloads:read",
        "test_runs:read",
        "reports:read", "reports:generate",
        "evidence:read",
        "threats:read", "incidents:read",
        "audit:read",
        "team:read",
    ],
    "viewer": [
        "workloads:read",
        "test_runs:read",
        "reports:read",
        "threats:read",
        "incidents:read",
        "team:read",
    ],
}


def has_permission(user_permissions: list[str], required: str) -> bool:
    return required in user_permissions


def require_permission(user_permissions: list[str], required: str) -> None:
    from fastapi import HTTPException
    if not has_permission(user_permissions, required):
        raise HTTPException(403, f"Permission required: {required}")
