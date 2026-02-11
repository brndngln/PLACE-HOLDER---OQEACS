from __future__ import annotations

from fastapi import APIRouter

from src.services.migration_checker import MigrationChecker
from src.services.query_optimizer import QueryOptimizer

router = APIRouter(prefix="/api/v1", tags=["queries"])


@router.post("/query/analyze")
def analyze(payload: dict):
    return QueryOptimizer().analyze_query(payload.get("sql", ""))


@router.post("/migration/check")
def migration(payload: dict):
    return MigrationChecker().check_safety(payload.get("sql", ""))
