from __future__ import annotations

import re

from src.models import Issue


class TypeScriptAnalyzer:
    def analyze(self, code: str) -> list[Issue]:
        issues: list[Issue] = []
        lines = code.splitlines()
        for i, line in enumerate(lines, start=1):
            if re.search(r":\s*any\b", line):
                issues.append(Issue(severity="medium", category="types", line=i, message="Use of any weakens type safety", suggestion="Use a specific type or generic constraint", rule_id="TS-ANY"))
            if "as any" in line:
                issues.append(Issue(severity="medium", category="types", line=i, message="Unsafe cast to any", suggestion="Avoid broad assertions", rule_id="TS-ASSERT"))
            if "promise.then(" in line and "catch(" not in code:
                issues.append(Issue(severity="medium", category="async", line=i, message="Potential unhandled rejection", suggestion="Add catch or use await try/catch", rule_id="TS-PROMISE"))
        return issues
