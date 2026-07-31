# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Override the DB session for tests so they never hit a real database."""
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
