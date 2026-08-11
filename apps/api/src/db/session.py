# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,      # drop dead connections before use
    pool_size=10,            # steady-state pooled connections (default was 5)
    max_overflow=20,         # burst headroom under concurrency (default was 10)
    pool_recycle=1800,       # recycle connections after 30 min to avoid staleness
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Alias used by the scheduler and other background tasks
async_session_factory = AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
