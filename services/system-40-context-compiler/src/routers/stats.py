"""GET /api/v1/stats — Context compilation statistics."""
from fastapi import APIRouter
import structlog

from src.models import ContextStats

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats", response_model=ContextStats)
async def get_stats() -> ContextStats:
    """Get context compilation statistics."""
    from src.main import get_effectiveness_tracker

    tracker = get_effectiveness_tracker()
    if tracker is None:
        return ContextStats(
            total_compilations=0,
            avg_tokens_used=0.0,
            avg_budget_used_pct=0.0,
            avg_quality_score=0.0,
            top_sources=[],
            compilations_today=0,
        )

    stats = await tracker.get_stats(days=30)
    return ContextStats(
        total_compilations=stats.get("total_compilations", 0),
        avg_tokens_used=0.0,
        avg_budget_used_pct=0.0,
        avg_quality_score=stats.get("avg_quality_score", 0.0),
        top_sources=[],
        compilations_today=0,
    )
