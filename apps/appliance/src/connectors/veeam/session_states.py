# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Veeam B&R session-state handling for instant-recovery sessions.

The Veeam REST API reports a session ``state`` string. For an instant-recovery
session the mount is published and the recovered VM is available while the
session is in the ``Working`` state; ``Failed`` is terminal. This module gives
those literals names and a small classifier so workflow code does not compare
raw strings inline.

Reference: Veeam B&R REST API session state enum. Keep in sync with the live
server when validating against a lab (see ADR-003).

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/
"""
from __future__ import annotations

from enum import Enum


class VeeamSessionState(str, Enum):
    STARTING = "Starting"
    WORKING = "Working"       # instant-recovery mount published, VM available
    STOPPING = "Stopping"
    STOPPED = "Stopped"
    SUCCESS = "Success"
    FAILED = "Failed"
    WARNING = "Warning"
    UNKNOWN = "unknown"       # returned when the API omits a state field


# States in which an instant-recovery mount is published and the recovered VM
# is expected to be registered and powering on.
PUBLISHED_STATES: frozenset[str] = frozenset({VeeamSessionState.WORKING.value})

# Terminal states that mean the session will never become published.
FAILED_STATES: frozenset[str] = frozenset(
    {VeeamSessionState.FAILED.value, VeeamSessionState.STOPPED.value}
)


def is_recovery_published(state: str) -> bool:
    """True if the session state means the recovered VM is available."""
    return state in PUBLISHED_STATES


def is_terminal_failure(state: str) -> bool:
    """True if the session has failed and will not become published."""
    return state in FAILED_STATES
