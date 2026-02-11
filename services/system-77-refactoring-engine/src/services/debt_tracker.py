from __future__ import annotations

from collections import Counter

from src.models import RefactoringOpportunity, TechDebtReport


class DebtTracker:
    EFFORT_HOURS = {"low": 0.5, "medium": 2.0, "high": 6.0}

    def calculate_debt(self, opportunities: list[RefactoringOpportunity]) -> TechDebtReport:
        by_type = Counter(op.type for op in opportunities)
        total = 0.0
        for op in opportunities:
            total += self.EFFORT_HOURS.get(op.estimated_effort, 2.0)
        top = [f"{k}:{v}" for k, v in by_type.most_common(5)]
        return TechDebtReport(total_items=len(opportunities), by_type=dict(by_type), top_priority=top, estimated_total_hours=round(total, 2))
