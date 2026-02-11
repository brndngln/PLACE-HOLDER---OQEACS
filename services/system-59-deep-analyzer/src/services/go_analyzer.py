from __future__ import annotations

from src.models import Issue


class GoAnalyzer:
    def analyze(self, code: str) -> list[Issue]:
        issues: list[Issue] = []
        lines = code.splitlines()
        for i, line in enumerate(lines, start=1):
            if line.strip().startswith("go ") and "context" not in code:
                issues.append(Issue(severity="medium", category="concurrency", line=i, message="Goroutine without context cancellation", suggestion="Pass context and cancellation path", rule_id="GO-GOROUTINE"))
            if "_, err :=" in line and "if err != nil" not in "\n".join(lines[i : i + 3]):
                issues.append(Issue(severity="medium", category="errors", line=i, message="Error value may be ignored", suggestion="Handle err explicitly", rule_id="GO-ERR"))
            if "defer" in line and "for " in "\n".join(lines[max(0, i - 3) : i + 1]):
                issues.append(Issue(severity="low", category="resources", line=i, message="Defer inside loop can accumulate", suggestion="Close explicitly or move defer outside loop", rule_id="GO-DEFER-LOOP"))
        return issues
