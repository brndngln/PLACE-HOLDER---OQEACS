"""Shared test fixtures for System 49: Execution Verification Loop."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import Settings
from src.models import ExecutionRequest, TestCase
from src.services.sandbox import SandboxExecutor
from src.services.test_runner import TestRunner
from src.services.verifier import VerificationLoop


@pytest.fixture()
def settings() -> Settings:
    """Return a Settings instance with test-friendly defaults."""
    return Settings(
        SERVICE_NAME="omni-exec-verify-test",
        SERVICE_PORT=9653,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test_exec_verify",
        REDIS_URL="redis://localhost:6379/15",
        EXECUTION_TIMEOUT_SECONDS=10,
        MAX_RETRIES=2,
        MAX_MEMORY_MB=128,
        LITELLM_URL="http://localhost:4000",
        MATTERMOST_WEBHOOK_URL="",
    )


@pytest.fixture()
def sandbox(settings: Settings) -> SandboxExecutor:
    """Return a SandboxExecutor wired to test settings."""
    return SandboxExecutor(settings=settings)


@pytest.fixture()
def test_runner(settings: Settings, sandbox: SandboxExecutor) -> TestRunner:
    """Return a TestRunner wired to test settings."""
    return TestRunner(settings=settings, sandbox=sandbox)


@pytest.fixture()
def verifier(
    settings: Settings,
    sandbox: SandboxExecutor,
    test_runner: TestRunner,
) -> VerificationLoop:
    """Return a VerificationLoop with no Redis."""
    return VerificationLoop(
        settings=settings,
        sandbox=sandbox,
        test_runner=test_runner,
        redis_client=None,
    )


@pytest.fixture()
def sample_execution_request() -> ExecutionRequest:
    """Return a simple Python execution request."""
    return ExecutionRequest(
        code='def main():\n    return 42\n\nprint(main())',
        language="python",
        test_cases=None,
        dependencies=[],
        entry_point="main",
    )


@pytest.fixture()
def sample_test_cases() -> list[TestCase]:
    """Return sample test cases."""
    return [
        TestCase(
            input={},
            expected_output=42,
            description="Should return 42",
        ),
        TestCase(
            input={},
            expected_output=42,
            description="Should still return 42",
        ),
    ]


@pytest.fixture()
async def async_client() -> AsyncClient:
    """Return an async HTTP client bound to the FastAPI app."""
    from src.main import app

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture()
def anyio_backend() -> str:
    """Constrain AnyIO tests to asyncio backend for subprocess compatibility."""
    return "asyncio"
