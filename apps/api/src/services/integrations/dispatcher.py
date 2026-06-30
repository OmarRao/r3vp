"""Route integration events to the correct connector."""
# Author: Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


async def dispatch_event(
    integration_type: str,
    config: dict[str, Any],
    event_type: str,
    payload: dict[str, Any],
) -> tuple[bool, str | None, int]:
    """
    Dispatch an event to the configured integration.
    Returns (success, error_detail, response_ms).
    """
    start = time.monotonic()
    try:
        if integration_type == "servicenow":
            from .servicenow import send_incident
            await send_incident(config, event_type, payload)
        elif integration_type == "jira":
            from .jira import create_issue
            await create_issue(config, event_type, payload)
        elif integration_type == "pagerduty":
            from .pagerduty import trigger_alert
            await trigger_alert(config, event_type, payload)
        elif integration_type == "splunk":
            from .splunk import send_hec_event
            await send_hec_event(config, event_type, payload)
        elif integration_type == "qradar":
            from .splunk import send_syslog_cef
            await send_syslog_cef(config, event_type, payload)
        elif integration_type == "sentinel":
            from .sentinel import send_log_analytics
            await send_log_analytics(config, event_type, payload)
        else:
            return False, f"Unknown integration type: {integration_type}", 0
        ms = round((time.monotonic() - start) * 1000)
        return True, None, ms
    except Exception as exc:
        ms = round((time.monotonic() - start) * 1000)
        logger.exception("Integration dispatch failed: %s", integration_type)
        return False, str(exc), ms
