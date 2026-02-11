from __future__ import annotations

from src.models import RefactoringOpportunity
from src.services.debt_tracker import DebtTracker


def _op(kind: str, effort: str) -> RefactoringOpportunity:
    return RefactoringOpportunity(id=kind, file_path="a.py", type=kind, description="d", risk="medium", estimated_effort=effort)


def test_calculate_debt() -> None:
    report = DebtTracker().calculate_debt([_op("duplication", "medium")])
    assert report.total_items == 1


def test_hours_positive() -> None:
    report = DebtTracker().calculate_debt([_op("duplication", "high"), _op("dead_code", "low")])
    assert report.estimated_total_hours > 0


def test_top_priority_list() -> None:
    report = DebtTracker().calculate_debt([_op("duplication", "medium")])
    assert isinstance(report.top_priority, list)
