# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Unit tests for Veeam instant-recovery session-state classification."""
from src.connectors.veeam.session_states import (
    VeeamSessionState,
    is_recovery_published,
    is_terminal_failure,
)


def test_working_is_published():
    assert is_recovery_published(VeeamSessionState.WORKING.value) is True
    assert is_recovery_published("Working") is True


def test_non_working_states_are_not_published():
    for state in ("Starting", "Stopping", "Success", "Failed", "unknown", ""):
        assert is_recovery_published(state) is False


def test_terminal_failure_states():
    assert is_terminal_failure("Failed") is True
    assert is_terminal_failure("Stopped") is True


def test_published_and_transient_states_are_not_terminal_failures():
    for state in ("Working", "Starting", "unknown"):
        assert is_terminal_failure(state) is False


def test_enum_values_match_veeam_literals():
    # Guards against accidental renaming of the wire literals.
    assert VeeamSessionState.WORKING.value == "Working"
    assert VeeamSessionState.FAILED.value == "Failed"
    assert VeeamSessionState.UNKNOWN.value == "unknown"
