"""
Helper to load per-org integration configs for SOAR, SIEM, and VeeamONE.

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy -- https://www.linkedin.com/in/omarrao/
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import NotificationChannel


async def get_org_integration_configs(
    db: AsyncSession, org_id: uuid.UUID
) -> dict:
    """
    Return integration configs for an org, pulled from the notification_channels table.

    SOAR channels have channel_type="soar", SIEM channels have "siem",
    VeeamONE has "veeamone". Regular notification channels (email/slack/teams)
    are returned in the "channels" list.
    """
    rows = (
        await db.execute(
            select(NotificationChannel).where(
                NotificationChannel.org_id == org_id,
                NotificationChannel.enabled == True,  # noqa: E712
            )
        )
    ).scalars().all()

    result: dict = {"channels": []}
    for row in rows:
        if row.channel_type == "soar":
            result["soar"] = {
                "platform": row.name,
                "url": row.destination,
                "api_key": "",  # Stored encrypted, placeholder
            }
        elif row.channel_type == "siem":
            result["siem"] = {
                "host": row.destination.split(":")[0],
                "port": int(row.destination.split(":")[1]) if ":" in row.destination else 514,
                "protocol": "udp",
                "format": "cef",
            }
        elif row.channel_type == "veeamone":
            parts = row.destination.split("|")
            result["veeamone"] = {
                "url": parts[0] if parts else row.destination,
                "username": parts[1] if len(parts) > 1 else "",
                "password": parts[2] if len(parts) > 2 else "",
            }
        else:
            result["channels"].append({
                "name": row.name,
                "channel_type": row.channel_type,
                "destination": row.destination,
                "events": row.events,
                "enabled": row.enabled,
            })
    return result
