"""Integration test fixtures - requires a running Postgres instance."""
from __future__ import annotations

import os
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Override settings before importing anything else
os.environ.setdefault("R3VP_API_DATABASE_URL", "postgresql+asyncpg://r3vp:r3vp@localhost:5432/r3vp_test")
os.environ.setdefault("R3VP_API_AUTH0_DOMAIN", "test.auth0.com")
os.environ.setdefault("R3VP_API_AUTH0_AUDIENCE", "test-audience")

from src.models.base import Base

TEST_DB_URL = os.environ["R3VP_API_DATABASE_URL"]


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
