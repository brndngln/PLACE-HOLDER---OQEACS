"""System 46 — Quick review API router."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from src.config import Settings
from src.models import QuickReviewRequest, QuickReviewResult
from src.services.quick_review import quick_review

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["review"])

_settings: Settings | None = None


def set_settings(settings: Settings) -> None:
    """Wire settings from the lifespan handler."""
    global _settings  # noqa: PLW0603
    _settings = settings


@router.post("/review", response_model=QuickReviewResult)
async def run_quick_review(request: QuickReviewRequest) -> QuickReviewResult:
    """Run a quick multi-agent code review."""
    settings = _settings or Settings()
    logger.info("quick_review_requested", language=request.language, code_len=len(request.code))
    return await quick_review(request, settings)
