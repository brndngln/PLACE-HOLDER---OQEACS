from __future__ import annotations

from fastapi import APIRouter

from src.services.debt_tracker import DebtTracker
from src.services.opportunity_detector import OpportunityDetector
from src.services.refactoring_executor import RefactoringExecutor

router = APIRouter(prefix="/api/v1", tags=["refactor"])


@router.post("/scan")
def scan(payload: dict):
    return OpportunityDetector().scan(payload.get("code", ""), payload.get("language", "python"))


@router.post("/refactor")
def refactor(payload: dict):
    from src.models import RefactoringOpportunity

    op = RefactoringOpportunity(**payload["opportunity"])
    return RefactoringExecutor().execute(op, payload.get("code", ""))


@router.get("/tech-debt")
def debt():
    ops = OpportunityDetector().scan("def x():\n    if a:\n        if b:\n            pass\n")
    return DebtTracker().calculate_debt(ops)
