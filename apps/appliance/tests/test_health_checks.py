"""Unit tests for health check plugin framework."""
import pytest
from health_checks.base import BaseHealthCheck


def test_base_health_check_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseHealthCheck()  # type: ignore[abstract]
