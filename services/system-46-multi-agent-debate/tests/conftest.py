"""System 46 — Shared test fixtures."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import Settings
from src.main import app
from src.services.debate_engine import DebateEngine


@pytest.fixture
def settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
        REDIS_URL="redis://localhost:6379/15",
        LITELLM_URL="http://localhost:4000",
    )


@pytest.fixture
def engine(settings: Settings) -> DebateEngine:
    return DebateEngine(settings=settings)


@pytest.fixture
async def async_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
