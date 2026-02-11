"""System 46 — Debate API router."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

from src.models import DebateRequest, DebateResult
from src.services.debate_engine import DebateEngine

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["debate"])

_engine: DebateEngine | None = None


def set_engine(engine: DebateEngine) -> None:
    """Wire the debate engine from the lifespan handler."""
    global _engine  # noqa: PLW0603
    _engine = engine


@router.post("/debate", response_model=DebateResult)
async def start_debate(request: DebateRequest) -> DebateResult:
    """Start a new multi-agent debate on a coding task."""
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialised")
    logger.info("debate_requested", task=request.task_description[:80])
    result = await _engine.run_debate(request)
    logger.info(
        "debate_completed",
        debate_id=result.debate_id,
        status=result.status.value,
        consensus=round(result.consensus_score, 3),
    )
    return result


@router.get("/debate/{debate_id}", response_model=DebateResult)
async def get_debate(debate_id: str) -> DebateResult:
    """Retrieve a completed debate by ID."""
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialised")
    result = _engine.get_debate(debate_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Debate not found")
    return result


@router.get("/debates")
async def list_debates() -> list[dict[str, Any]]:
    """List all debate summaries."""
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialised")
    return _engine.list_debates()
