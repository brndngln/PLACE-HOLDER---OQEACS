from __future__ import annotations

from collections import defaultdict

from src.models import FlakyTestReport


class FlakyDetector:
    def detect_flaky(self, test_results_history: list[dict]) -> list[FlakyTestReport]:
        grouped: dict[str, list[bool]] = defaultdict(list)
        for row in test_results_history:
            grouped[row["test_name"]].append(bool(row["passed"]))

        out: list[FlakyTestReport] = []
        for test_name, runs in grouped.items():
            failures = runs.count(False)
            if failures == 0 or failures == len(runs):
                continue
            rate = failures / len(runs)
            out.append(
                FlakyTestReport(
                    test_name=test_name,
                    file="tests/unknown.py",
                    failure_rate=round(rate, 3),
                    last_flake="recent",
                    root_cause_guess="timing/shared-state",
                )
            )
        return out
