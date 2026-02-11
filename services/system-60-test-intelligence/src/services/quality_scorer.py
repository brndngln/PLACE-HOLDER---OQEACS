from __future__ import annotations

import re

from src.models import TestQualityScore


class TestQualityScorer:
    def score_test_file(self, test_code: str, file: str = "tests.py") -> TestQualityScore:
        tests = re.findall(r"def\s+test_", test_code)
        total = len(tests)
        issues: list[str] = []

        assertion_count = len(re.findall(r"assert\s+", test_code))
        if assertion_count == 0:
            issues.append("No assertions found")
        if "assert True" in test_code:
            issues.append("Contains weak assertion `assert True`")
        if "TODO" in test_code:
            issues.append("Contains unfinished TODO")

        effective = max(0, total - len(issues))
        score = 100.0 if total == 0 else max(0.0, round((effective / max(total, 1)) * 100 - len(issues) * 5, 2))
        return TestQualityScore(file=file, total_tests=total, effective_tests=effective, quality_score=score, issues=issues)
