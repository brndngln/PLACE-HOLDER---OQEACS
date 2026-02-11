"""
System 43 — Shared pytest fixtures.

Provides an async HTTPX test client wired to the FastAPI app, plus
a standalone TestRunner instance with Redis disabled for unit tests.
"""

from __future__ import annotations

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.config import Settings
from src.main import app
from src.services.test_runner import TestRunner


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Return a Settings instance with test-safe defaults."""
    return Settings(
        SERVICE_NAME="self-testing-test",
        SERVICE_PORT=9636,
        DATABASE_URL="postgresql+asyncpg://omni:omni@localhost:5432/omni_self_testing_test",
        REDIS_URL="redis://localhost:6379/15",
        MATTERMOST_WEBHOOK_URL="http://localhost:8065/hooks/test",
        SANDBOX_URL="http://localhost:9620",
        SCORING_URL="http://localhost:9623",
        RETROSPECTIVE_URL="http://localhost:9633",
    )


@pytest.fixture()
def runner(settings: Settings) -> TestRunner:
    """Provide a TestRunner with no Redis for isolated unit tests."""
    return TestRunner(settings=settings, redis_client=None)


@pytest_asyncio.fixture()
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Yield an async HTTPX client bound to the FastAPI ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
