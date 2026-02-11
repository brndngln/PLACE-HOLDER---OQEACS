from __future__ import annotations

from src.models import TestImpactResult


class TestImpactAnalyzer:
    def analyze_impact(self, changed_files: list[str], test_map: dict[str, list[str]]) -> TestImpactResult:
        affected: list[str] = []
        for changed in changed_files:
            affected.extend(test_map.get(changed, []))
        unique = sorted(set(affected))
        return TestImpactResult(
            changed_files=changed_files,
            affected_tests=unique,
            priority_order=unique,
            estimated_time=round(len(unique) * 1.25, 2),
        )
