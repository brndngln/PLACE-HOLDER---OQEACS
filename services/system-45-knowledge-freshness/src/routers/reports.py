"""Reports API router — deprecations and weekly reports.

System 45 - Knowledge Freshness Service.
"""

import structlog
from fastapi import APIRouter, HTTPException, Request

from src.models import DeprecationWarning, WeeklyReport

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["reports"])


@router.get("/deprecations", response_model=list[DeprecationWarning])
async def list_deprecations(request: Request) -> list[DeprecationWarning]:
    """List tracked deprecation warnings from the database.

    Args:
        request: FastAPI request (used to access app state).

    Returns:
        List of DeprecationWarning objects ordered by detection date descending.
    """
    freshness_service = request.app.state.freshness_service
    try:
        deprecations = await freshness_service.get_deprecations()
        logger.info("deprecations_listed", count=len(deprecations))
        return deprecations
    except Exception as exc:
        logger.error("deprecations_list_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve deprecations: {exc}"
        ) from exc


@router.get("/report", response_model=WeeklyReport)
async def get_weekly_report(request: Request) -> WeeklyReport:
    """Generate or retrieve the latest weekly knowledge freshness report.

    Tries to return a cached report from Redis first.  Falls back to
    generating a fresh report on-demand.

    Args:
        request: FastAPI request.

    Returns:
        The current WeeklyReport.
    """
    redis_client = getattr(request.app.state, "redis_client", None)

    # Try cached report first
    if redis_client is not None:
        try:
            cached = await redis_client.get("freshness:weekly_report")
            if cached:
                logger.info("weekly_report_served_from_cache")
                return WeeklyReport.model_validate_json(cached)
        except Exception as exc:
            logger.warning("redis_cache_read_error", error=str(exc))

    # Generate fresh report
    freshness_service = request.app.state.freshness_service
    try:
        report = await freshness_service.generate_weekly_report()
        logger.info("weekly_report_generated_on_demand")
        return report
    except Exception as exc:
        logger.error("weekly_report_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to generate report: {exc}"
        ) from exc
