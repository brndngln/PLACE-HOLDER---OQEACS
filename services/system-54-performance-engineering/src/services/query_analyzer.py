from __future__ import annotations

import re

from src.models import N1QueryDetection


class QueryAnalyzer:
    def detect_n_plus_one(self, code: str) -> list[N1QueryDetection]:
        findings: list[N1QueryDetection] = []
        lines = code.splitlines()
        for i, line in enumerate(lines, start=1):
            lower = line.lower()
            if "for " in lower:
                window = "\n".join(lines[i : i + 6]).lower()
                if "select" in window or "session.query" in window:
                    findings.append(N1QueryDetection(line=i, pattern="loop_with_query", suggestion="Batch query outside loop or eager load"))
            if re.search(r"select\s+\*", lower):
                findings.append(N1QueryDetection(line=i, pattern="select_star", suggestion="Select explicit columns"))
            if re.search(r"update\s+\w+\s+set", lower) and "where" not in lower:
                findings.append(N1QueryDetection(line=i, pattern="update_without_where", suggestion="Add WHERE clause"))
            if re.search(r"delete\s+from\s+\w+", lower) and "where" not in lower:
                findings.append(N1QueryDetection(line=i, pattern="delete_without_where", suggestion="Add WHERE clause"))
        return findings
