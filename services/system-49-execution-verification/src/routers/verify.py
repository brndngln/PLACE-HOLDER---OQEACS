"""API routes for code verification and execution."""

from __future__ import annotations

import time

import structlog
from fastapi import APIRouter, HTTPException
from prometheus_client import Counter, Histogram

from src.models import ExecutionRequest, ExecutionResult, VerificationResult
from src.services.sandbox import SandboxExecutor
from src.services.verifier import VerificationLoop

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["verification"])

# Prometheus metrics
VERIFY_COUNT = Counter(
    "exec_verify_total",
    "Total verification requests",
    ["language", "status"],
)
VERIFY_LATENCY = Histogram(
    "exec_verify_duration_seconds",
    "Verification loop duration",
    ["language"],
)
EXECUTE_COUNT = Counter(
    "exec_execute_total",
    "Total single-execution requests",
    ["language", "success"],
)

# Module-level references set during lifespan
_verifier: VerificationLoop | None = None
_sandbox: SandboxExecutor | None = None
_redis = None


def set_services(
    verifier: VerificationLoop,
    sandbox: SandboxExecutor,
    redis_client=None,
) -> None:
    """Wire runtime services into the router (called from lifespan)."""
    global _verifier, _sandbox, _redis
    _verifier = verifier
    _sandbox = sandbox
    _redis = redis_client


# ------------------------------------------------------------------
# POST /api/v1/verify — full verification loop
# ------------------------------------------------------------------


@router.post("/verify", response_model=VerificationResult)
async def verify_code(request: ExecutionRequest) -> VerificationResult:
    """Run the full verification loop: execute, test, regenerate on failure."""
    if _verifier is None:
        raise HTTPException(status_code=503, detail="Verifier not initialized")

    start = time.monotonic()
    logger.info("verify_request", language=request.language, code_len=len(request.code))

    result = await _verifier.verify(request)

    elapsed = time.monotonic() - start
    VERIFY_COUNT.labels(language=request.language, status=result.final_status).inc()
    VERIFY_LATENCY.labels(language=request.language).observe(elapsed)

    logger.info(
        "verify_complete",
        language=request.language,
        status=result.final_status,
        attempts=result.attempts,
        elapsed_s=round(elapsed, 2),
    )
    return result


# ------------------------------------------------------------------
# POST /api/v1/execute — single execution (no loop)
# ------------------------------------------------------------------


@router.post("/execute", response_model=ExecutionResult)
async def execute_code(request: ExecutionRequest) -> ExecutionResult:
    """Execute code once without the verification/regeneration loop."""
    if _sandbox is None:
        raise HTTPException(status_code=503, detail="Sandbox not initialized")

    logger.info("execute_request", language=request.language, code_len=len(request.code))

    result = await _sandbox.execute(
        code=request.code,
        language=request.language,
        dependencies=request.dependencies,
    )

    EXECUTE_COUNT.labels(language=request.language, success=str(result.success)).inc()
    return result


# ------------------------------------------------------------------
# GET /api/v1/results/{result_id} — retrieve stored result
# ------------------------------------------------------------------


@router.get("/results/{result_id}", response_model=VerificationResult)
async def get_result(result_id: str) -> VerificationResult:
    """Retrieve a stored verification result by its ID."""
    if _redis is None:
        raise HTTPException(status_code=503, detail="Redis not available")

    key = f"exec_verify:result:{result_id}"
    data = await _redis.get(key)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")

    return VerificationResult.model_validate_json(data)
