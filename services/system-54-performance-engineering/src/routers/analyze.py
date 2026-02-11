from __future__ import annotations

from fastapi import APIRouter

from src.models import AnalyzeRequest
from src.services.complexity_analyzer import ComplexityAnalyzer
from src.services.memory_analyzer import MemoryAnalyzer
from src.services.query_analyzer import QueryAnalyzer

router = APIRouter(prefix="/api/v1/analyze", tags=["analyze"])


@router.post("/complexity")
def complexity(req: AnalyzeRequest):
    return ComplexityAnalyzer().analyze_complexity(req.code, req.language)


@router.post("/queries")
def queries(req: AnalyzeRequest):
    return QueryAnalyzer().detect_n_plus_one(req.code)


@router.post("/memory")
def memory(req: AnalyzeRequest):
    return MemoryAnalyzer().detect_leaks(req.code)
