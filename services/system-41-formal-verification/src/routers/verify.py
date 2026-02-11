"""POST /api/v1/verify — Submit code for formal verification."""
from fastapi import APIRouter, HTTPException
import structlog

from src.models import ProofRecord, VerificationRequest, VerificationResult

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["verify"])


@router.post("/verify", response_model=VerificationResult)
async def submit_verification(request: VerificationRequest) -> VerificationResult:
    """Submit code for formal verification."""
    from src.main import get_verifier

    verifier = get_verifier()
    if verifier is None:
        raise HTTPException(status_code=503, detail="Verifier not initialized")
    return await verifier.verify(request)


@router.get("/verify/{result_id}", response_model=VerificationResult)
async def get_verification(result_id: str) -> VerificationResult:
    """Check verification status and get results."""
    from src.main import get_verifier

    verifier = get_verifier()
    if verifier is None:
        raise HTTPException(status_code=503, detail="Verifier not initialized")

    result = await verifier.get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    return result


@router.get("/verify/{result_id}/report")
async def get_verification_report(result_id: str) -> dict:
    """Get a human-readable verification report."""
    from src.main import get_verifier

    verifier = get_verifier()
    if verifier is None:
        raise HTTPException(status_code=503, detail="Verifier not initialized")

    result = await verifier.get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")

    return {
        "id": result.id,
        "status": result.status.value,
        "tool": result.tool.value,
        "summary": (
            f"Verification {result.status.value}: "
            f"{len(result.properties_passed)}/{len(result.properties_checked)} properties passed"
        ),
        "properties_passed": result.properties_passed,
        "properties_failed": result.properties_failed,
        "counterexamples": [ce.model_dump() for ce in result.counterexamples],
        "execution_time_ms": result.execution_time_ms,
    }


@router.get("/proofs", response_model=list[ProofRecord])
async def list_proofs(project_id: str | None = None, limit: int = 50) -> list[ProofRecord]:
    """List completed verification proofs."""
    from src.main import get_verifier

    verifier = get_verifier()
    if verifier is None:
        raise HTTPException(status_code=503, detail="Verifier not initialized")
    return await verifier.list_proofs(project_id=project_id, limit=limit)
