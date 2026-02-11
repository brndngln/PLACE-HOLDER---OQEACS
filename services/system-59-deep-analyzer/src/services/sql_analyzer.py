from __future__ import annotations

import re

from src.models import Issue


class SQLAnalyzer:
    def analyze(self, code: str) -> list[Issue]:
        issues: list[Issue] = []
        lines = code.splitlines()
        for i, line in enumerate(lines, start=1):
            l = line.lower()
            if re.search(r"select\s+\*", l):
                issues.append(Issue(severity="low", category="performance", line=i, message="SELECT * usage", suggestion="Select only needed columns", rule_id="SQL-SELECT-STAR"))
            if ("update " in l or "delete from" in l) and "where" not in l:
                issues.append(Issue(severity="high", category="safety", line=i, message="Mutation query missing WHERE", suggestion="Constrain mutation with WHERE", rule_id="SQL-WHERE"))
            if "like '%" in l:
                issues.append(Issue(severity="medium", category="performance", line=i, message="Leading wildcard LIKE may skip indexes", suggestion="Use full-text index or prefix search", rule_id="SQL-LIKE"))
            if "+" in line and "select" in l:
                issues.append(Issue(severity="high", category="security", line=i, message="Possible SQL injection string concatenation", suggestion="Use parameterized queries", rule_id="SQL-INJECTION"))
        return issues
