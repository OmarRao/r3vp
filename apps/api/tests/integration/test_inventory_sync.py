"""Integration test: inventory sync upserts workloads correctly."""
from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select

from src.models.appliance import Org, Appliance
from src.models.workload import Workload
from src.services.appliance import accept_inventory_sync

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_inventory_sync_upsert(db_session):
    """Syncing VMs creates workloads; re-syncing updates them without duplicates."""
    org_id = uuid.uuid4()
    appliance_id = uuid.uuid4()

    db_session.add(Org(id=org_id, name="Test Org"))
    db_session.add(Appliance(
        id=appliance_id, org_id=org_id, name="test-appliance",
        mtls_thumbprint="abc123", status="active"
    ))
    await db_session.commit()

    vms = [
        {"object_id": "vm-001", "name": "dc-01", "platform": "vmware",
         "os_type": "windows", "is_protected": True, "last_backup": None, "moref": "vm-001"},
        {"object_id": "vm-002", "name": "sql-01", "platform": "vmware",
         "os_type": "windows", "is_protected": True, "last_backup": None, "moref": "vm-002"},
    ]

    count = await accept_inventory_sync(db_session, appliance_id=appliance_id, org_id=org_id, vms=vms)
    assert count == 2

    rows = await db_session.execute(
        select(Workload).where(Workload.appliance_id == appliance_id)
    )
    workloads = rows.scalars().all()
    assert len(workloads) == 2
    names = {w.name for w in workloads}
    assert names == {"dc-01", "sql-01"}

    # Re-sync with updated name - should update, not duplicate
    vms[0]["name"] = "dc-01-updated"
    count2 = await accept_inventory_sync(db_session, appliance_id=appliance_id, org_id=org_id, vms=vms)
    assert count2 == 2

    rows2 = await db_session.execute(
        select(Workload).where(Workload.appliance_id == appliance_id)
    )
    workloads2 = rows2.scalars().all()
    assert len(workloads2) == 2
    names2 = {w.name for w in workloads2}
    assert "dc-01-updated" in names2
