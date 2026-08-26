# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Override the DB session for tests so they never hit a real database."""
import os

# Disable per-client rate limiting for the shared app used across the suite so
# many requests in one window do not cross-contaminate tests. The limiter is
# exercised on its own fresh app in tests/test_rate_limit.py. Must be set before
# src.config / src.main are imported below.
os.environ.setdefault("R3VP_API_RATE_LIMIT_ENABLED", "false")

from unittest.mock import AsyncMock

import pytest

from src.db.session import get_db
from src.main import app


@pytest.fixture(autouse=True)
def override_db():
    """Replace the DB dependency with a no-op mock for all tests."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    async def _mock_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _mock_get_db
    yield
    app.dependency_overrides.clear()
