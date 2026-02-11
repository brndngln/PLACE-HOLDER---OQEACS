from __future__ import annotations

from fastapi import APIRouter

from src.models import AnalysisRequest, LanguageSupport
from src.services.analyzer_registry import AnalyzerRegistry

router = APIRouter(prefix="/api/v1", tags=["analyze"])
_registry = AnalyzerRegistry()


@router.post("/analyze")
def analyze(req: AnalysisRequest):
    return _registry.analyze(req.code, req.language)


@router.get("/languages", response_model=LanguageSupport)
def languages() -> LanguageSupport:
    return LanguageSupport(
        languages=[
            {"name": "python", "capabilities": ["async", "exceptions", "defaults"]},
            {"name": "typescript", "capabilities": ["type-safety", "promises"]},
            {"name": "sql", "capabilities": ["injection", "performance"]},
            {"name": "go", "capabilities": ["goroutines", "error handling"]},
        ]
    )
