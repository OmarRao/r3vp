from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db

router = APIRouter()


@router.get("/{run_id}")
async def list_evidence(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list:
    # Returns list of presigned S3 URLs for all evidence artifacts in this run
    return []
