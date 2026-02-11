"""Shared pytest fixtures for System 45 - Knowledge Freshness Service tests."""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.freshness import FreshnessService


@pytest.fixture()
def mock_freshness_service() -> FreshnessService:
    """Return a FreshnessService with all external dependencies mocked."""
    service = FreshnessService(
        qdrant_client=None,
        http_client=None,
        db_pool=None,
        redis_client=None,
    )
    return service


@pytest.fixture()
def client(mock_freshness_service: FreshnessService) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient with mocked application state.

    External services (database, Redis, Qdrant, scheduler) are stubbed
    so that tests can run without any infrastructure.
    """
    # Override lifespan by manually setting state
    app.state.db_pool = None
    app.state.redis_client = None
    app.state.qdrant_client = None
    app.state.http_client = None
    app.state.freshness_service = mock_freshness_service

    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = [
        {"id": "full_scan", "name": "Full Feed Scan", "next_run_time": "2026-01-01T00:00:00"},
        {"id": "security_scan", "name": "Security Scan", "next_run_time": "2026-01-01T01:00:00"},
        {"id": "weekly_report", "name": "Weekly Report", "next_run_time": "2026-01-06T09:00:00"},
    ]
    app.state.scheduler = mock_scheduler

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
