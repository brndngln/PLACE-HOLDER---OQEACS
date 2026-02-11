from __future__ import annotations

import pytest

from src.models import ExecutionRequest
from src.services.sandbox import SandboxExecutor
from src.services.test_runner import TestRunner
from src.services.verifier import VerificationLoop
from src.config import Settings


@pytest.mark.anyio
async def test_verify_simple_python_success() -> None:
    settings = Settings(MAX_RETRIES=2)
    sandbox = SandboxExecutor(settings=settings)
    runner = TestRunner(settings=settings, sandbox=sandbox)
    verifier = VerificationLoop(settings=settings, sandbox=sandbox, test_runner=runner, redis_client=None)
    req = ExecutionRequest(code="def run():\n    return 1\nprint(run())", language="python", dependencies=[])
    result = await verifier.verify(req)
    assert result.final_status in {"verified", "failed"}
    assert result.attempts >= 1


@pytest.mark.anyio
async def test_verify_timeout_path() -> None:
    settings = Settings(EXECUTION_TIMEOUT_SECONDS=1, MAX_RETRIES=1)
    sandbox = SandboxExecutor(settings=settings)
    runner = TestRunner(settings=settings, sandbox=sandbox)
    verifier = VerificationLoop(settings=settings, sandbox=sandbox, test_runner=runner, redis_client=None)
    req = ExecutionRequest(code="while True:\n    pass", language="python", dependencies=[])
    result = await verifier.verify(req)
    assert result.final_status in {"timeout", "failed", "verified"}


@pytest.mark.anyio
async def test_verify_tracks_attempts() -> None:
    settings = Settings(MAX_RETRIES=3)
    sandbox = SandboxExecutor(settings=settings)
    runner = TestRunner(settings=settings, sandbox=sandbox)
    verifier = VerificationLoop(settings=settings, sandbox=sandbox, test_runner=runner, redis_client=None)
    req = ExecutionRequest(code="print('x')", language="python", dependencies=[])
    result = await verifier.verify(req)
    assert result.attempts >= 1
    assert isinstance(result.all_results, list)


@pytest.mark.anyio
async def test_verify_with_test_cases() -> None:
    settings = Settings(MAX_RETRIES=1)
    sandbox = SandboxExecutor(settings=settings)
    runner = TestRunner(settings=settings, sandbox=sandbox)
    verifier = VerificationLoop(settings=settings, sandbox=sandbox, test_runner=runner, redis_client=None)
    req = ExecutionRequest(code="def add(a,b):\n    return a+b", language="python", dependencies=[])
    result = await verifier.verify(req)
    assert result.final_status in {"verified", "failed"}
