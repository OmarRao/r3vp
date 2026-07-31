# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

from __future__ import annotations

from .base import BaseHealthCheck


class MSSQLHealthCheck(BaseHealthCheck):
    name = "mssql_query"

    async def run(self, vm_moref: str) -> dict:
        # In production: run `SELECT 1` via pyodbc against the recovered VM's SQL Server
        # Validates that SQL Server service started and can accept connections
        return {"passed": False, "output": "not implemented", "check": self.name}
