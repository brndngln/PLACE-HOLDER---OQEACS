"""API routes for test generation and execution."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException

from src.models import TestCase, TestCaseResult, TestGenerationRequest, TestRunRequest
from src.services.test_runner import TestRunner

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["tests"])

# Module-level reference set during lifespan
_test_runner: TestRunner | None = None


def set_test_runner(runner: TestRunner) -> None:
    """Wire the test runner into the router (called from lifespan)."""
    global _test_runner
    _test_runner = runner


# ------------------------------------------------------------------
# POST /api/v1/generate-tests
# ------------------------------------------------------------------


@router.post("/generate-tests", response_model=list[TestCase])
async def generate_tests(request: TestGenerationRequest) -> list[TestCase]:
    """Auto-generate test cases for the provided code using LiteLLM."""
    if _test_runner is None:
        raise HTTPException(status_code=503, detail="Test runner not initialized")

    logger.info("generate_tests_request", language=request.language, code_len=len(request.code))

    tests = await _test_runner.auto_generate_tests(request.code, request.language)

    logger.info("tests_generated", count=len(tests), language=request.language)
    return tests


# ------------------------------------------------------------------
# POST /api/v1/run-tests
# ------------------------------------------------------------------


@router.post("/run-tests", response_model=list[TestCaseResult])
async def run_tests(request: TestRunRequest) -> list[TestCaseResult]:
    """Run the provided test cases against the given code."""
    if _test_runner is None:
        raise HTTPException(status_code=503, detail="Test runner not initialized")

    logger.info(
        "run_tests_request",
        language=request.language,
        code_len=len(request.code),
        test_count=len(request.test_cases),
    )

    results = await _test_runner.run_tests(
        request.code, request.test_cases, request.language
    )

    passed = sum(1 for r in results if r.passed)
    logger.info(
        "tests_complete",
        passed=passed,
        total=len(results),
        language=request.language,
    )
    return results
