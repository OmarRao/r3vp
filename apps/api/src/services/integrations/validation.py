# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Per-type config validation for outbound integrations.

Rejects an integration config at creation time when it is missing fields the
connector needs to dispatch, so failures surface immediately instead of silently
at the first real event. Pure and unit-testable.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/
"""
from __future__ import annotations

from typing import Any

from src.services.url_guard import UnsafeUrlError, check_scheme_and_literal

# Fields each connector must have to dispatch (from the connector implementations).
REQUIRED_FIELDS: dict[str, list[str]] = {
    "servicenow": ["instance_url", "api_token"],
    "jira": ["base_url", "api_token", "email", "project_key"],
    "pagerduty": ["routing_key"],
    "splunk": ["hec_url", "hec_token"],
    "qradar": ["syslog_host", "syslog_port"],
    "sentinel": ["workspace_id", "shared_key"],
}

# Fields that must be http(s) URLs when present.
URL_FIELDS: frozenset[str] = frozenset({"instance_url", "base_url", "hec_url"})


def validate_integration_config(integration_type: str, config: dict[str, Any]) -> list[str]:
    """Return a list of human-readable config errors (empty when valid)."""
    required = REQUIRED_FIELDS.get(integration_type)
    if required is None:
        return [f"Unknown integration type: {integration_type}"]

    errors: list[str] = []
    for field in required:
        value = config.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"Missing required config field: {field}")

    for field in URL_FIELDS:
        value = config.get(field)
        if not value:
            continue
        # Reject non-http(s) schemes and any literal private/loopback/link-local
        # (e.g. cloud metadata) address at config time. Hostnames are re-checked
        # with full DNS resolution at dispatch time (see services.url_guard).
        try:
            check_scheme_and_literal(str(value))
        except UnsafeUrlError as exc:
            errors.append(f"{field} is not an allowed URL: {exc}")

    if integration_type == "qradar":
        port = config.get("syslog_port")
        if port is not None:
            try:
                port_num = int(port)
            except (TypeError, ValueError):
                errors.append("syslog_port must be a number")
            else:
                if not (1 <= port_num <= 65535):
                    errors.append("syslog_port must be between 1 and 65535")

    return errors
