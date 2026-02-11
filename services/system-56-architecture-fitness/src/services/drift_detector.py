from __future__ import annotations

from src.models import Violation


class DriftDetector:
    def detect_drift(self, current_architecture: dict, baseline: dict) -> list[Violation]:
        violations: list[Violation] = []
        current_edges = {tuple(x) for x in current_architecture.get("edges", [])}
        baseline_edges = {tuple(x) for x in baseline.get("edges", [])}

        added = current_edges - baseline_edges
        for src, dst in sorted(added):
            violations.append(
                Violation(
                    rule="drift",
                    file=src,
                    message=f"New cross-boundary dependency introduced: {src} -> {dst}",
                    severity="medium",
                )
            )
        return violations
