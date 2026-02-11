"""
Shared pytest fixtures for System 42 tests.
"""

from __future__ import annotations

from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.health_monitor import AgentHealthMonitor


@pytest.fixture(name="client")
def fixture_client() -> Generator[TestClient, None, None]:
    """Provide a synchronous TestClient with mocked app state so tests
    can run without live Postgres / Redis / LiteLLM."""

    # Build a monitor that has no real DB pool
    monitor = AgentHealthMonitor(db_pool=None)

    # Attach mocked state
    app.state.db_pool = None
    app.state.redis = None
    app.state.monitor = monitor
    app.state.scheduler = MagicMock()

    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc
