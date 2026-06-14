from __future__ import annotations
from .base import BaseHealthCheck


class MSSQLHealthCheck(BaseHealthCheck):
    name = "mssql_query"

    async def run(self, vm_moref: str) -> dict:
        # In production: run `SELECT 1` via pyodbc against the recovered VM's SQL Server
        # Validates that SQL Server service started and can accept connections
        return {"passed": False, "output": "not implemented", "check": self.name}
