# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Base class for all health check plugins."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseHealthCheck(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, vm_moref: str) -> dict:
        """Run the health check. Returns {"passed": bool, "output": str}."""
        ...
