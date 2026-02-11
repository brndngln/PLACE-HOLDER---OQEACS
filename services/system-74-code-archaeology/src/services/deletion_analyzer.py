from __future__ import annotations

from pathlib import Path

from src.models import DeletionRisk


class DeletionAnalyzer:
    def assess_deletion_risk(self, repo_path: str, file: str, function: str) -> DeletionRisk:
        root = Path(repo_path)
        refs = 0
        for pyf in root.rglob("*.py"):
            text = pyf.read_text(errors="ignore")
            refs += text.count(function)
        risk = "high" if refs > 5 else "medium" if refs > 1 else "low"
        reason = "Function referenced across project" if refs > 1 else "Few references found"
        return DeletionRisk(file_path=file, function_name=function, risk_level=risk, dependents_count=max(refs - 1, 0), last_used="recent", reason=reason)
