# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Unit tests for health check plugin framework."""
import pytest
from health_checks.base import BaseHealthCheck


def test_base_health_check_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseHealthCheck()  # type: ignore[abstract]
