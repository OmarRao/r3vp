# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""MSSP partner provisioning.

`mssp_customer_orgs.mssp_id` and `mssp_alert_rules.mssp_id` are foreign keys to
`mssp_partners.id`, not org ids. The console endpoints must therefore resolve
the caller's org to its partner record (creating one on first use) instead of
using the org id directly as the partner id.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.mssp import MsspPartner


async def get_or_create_partner(
    db: AsyncSession, org_id: uuid.UUID, name: str | None = None
) -> MsspPartner:
    """Return the MSSP partner record for ``org_id``, creating it if absent.

    Idempotent: repeated calls for the same org return the same partner. The
    slug is derived deterministically from the org id so it is stable and
    unique.
    """
    partner = await db.scalar(select(MsspPartner).where(MsspPartner.org_id == org_id))
    if partner is not None:
        return partner

    partner = MsspPartner(
        org_id=org_id,
        name=name or f"Partner {str(org_id)[:8]}",
        slug=f"org-{org_id.hex[:12]}",
    )
    db.add(partner)
    await db.flush()
    return partner
