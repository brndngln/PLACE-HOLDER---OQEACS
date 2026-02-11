"""Impact analysis routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.models import AffectedEntity, ImpactAnalysisRequest, ImpactReport
from src.services.impact_analyzer import ImpactAnalyzer

router = APIRouter(prefix="/api/v1", tags=["impact"])

_impact_analyzer: ImpactAnalyzer | None = None


def wire(impact_analyzer: ImpactAnalyzer) -> None:
    global _impact_analyzer  # noqa: PLW0603
    _impact_analyzer = impact_analyzer


@router.post("/impact", response_model=ImpactReport)
async def analyze_impact(request: ImpactAnalysisRequest) -> ImpactReport:
    if _impact_analyzer is None:
        raise HTTPException(status_code=503, detail="Impact analyzer unavailable")
    if not request.repo_id:
        raise HTTPException(status_code=422, detail="repo_id is required")
    return _impact_analyzer.analyze_impact(
        repo_id=request.repo_id,
        file_path=request.file_path,
        function_name=request.function_name,
        change_description=request.change_description,
    )


@router.get("/entities/{entity_id}/dependents", response_model=list[AffectedEntity])
async def get_dependents(entity_id: str, repo_id: str = Query(...)) -> list[AffectedEntity]:
    if _impact_analyzer is None:
        raise HTTPException(status_code=503, detail="Impact analyzer unavailable")
    return _impact_analyzer.get_dependents(repo_id, entity_id)
