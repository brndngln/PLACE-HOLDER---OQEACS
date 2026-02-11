"""Updates API router — list, filter, and trigger scans.

System 45 - Knowledge Freshness Service.
"""

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from src.models import FeedCategory, KnowledgeUpdate, ScanReport

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/updates", tags=["updates"])


@router.get("", response_model=list[dict])
async def list_updates(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    category: Optional[FeedCategory] = Query(default=None, description="Filter by category"),
) -> list[dict]:
    """Retrieve recent knowledge updates from the vector store.

    Args:
        request: FastAPI request (used to access app state).
        limit: Maximum number of results.
        category: Optional category filter.

    Returns:
        List of update payloads.
    """
    freshness_service = request.app.state.freshness_service
    updates = await freshness_service.get_recent_updates(limit=limit, category=category)
    logger.info("updates_listed", count=len(updates), category=category)
    return updates


@router.get("/breaking", response_model=list[dict])
async def list_breaking_updates(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
) -> list[dict]:
    """Retrieve breaking change updates.

    Args:
        request: FastAPI request.
        limit: Maximum number of results.

    Returns:
        List of breaking change payloads.
    """
    freshness_service = request.app.state.freshness_service
    updates = await freshness_service.get_breaking_updates(limit=limit)
    logger.info("breaking_updates_listed", count=len(updates))
    return updates


@router.post("/scan", response_model=ScanReport)
async def trigger_scan(request: Request) -> ScanReport:
    """Trigger an immediate full feed scan.

    Args:
        request: FastAPI request.

    Returns:
        ScanReport with results of the scan.
    """
    freshness_service = request.app.state.freshness_service
    logger.info("manual_scan_triggered")
    try:
        report = await freshness_service.scan_all_feeds()
        return report
    except Exception as exc:
        logger.error("manual_scan_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Scan failed: {exc}") from exc
