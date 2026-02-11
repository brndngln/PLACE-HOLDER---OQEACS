"""POST /api/v1/compile — Context compilation endpoint."""
from fastapi import APIRouter, HTTPException
import structlog

from src.models import ContextRequest, ContextResponse, EffectivenessReport

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["compile"])


@router.post("/compile", response_model=ContextResponse)
async def compile_context(request: ContextRequest) -> ContextResponse:
    """Compile optimal context for an LLM invocation."""
    from src.main import get_compiler

    compiler = get_compiler()
    if compiler is None:
        raise HTTPException(status_code=503, detail="Compiler not initialized")

    result = await compiler.compile(request)
    logger.info(
        "compile_complete",
        task_id=request.task_id,
        tokens=result.total_tokens,
        pct=result.budget_used_pct,
    )
    return result


@router.post("/effectiveness")
async def report_effectiveness(report: EffectivenessReport) -> dict:
    """Report context effectiveness score for learning."""
    from src.main import get_effectiveness_tracker

    tracker = get_effectiveness_tracker()
    if tracker is None:
        raise HTTPException(status_code=503, detail="Tracker not initialized")

    await tracker.record(report, [])
    return {"status": "recorded", "task_id": report.task_id}
