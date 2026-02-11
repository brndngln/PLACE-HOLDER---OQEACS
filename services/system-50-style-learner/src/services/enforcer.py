from __future__ import annotations

import re

from src.models import StyleCheckResult, StyleProfile, StyleViolation


class StyleEnforcer:
    def check_code(self, code: str, profile: StyleProfile) -> StyleCheckResult:
        violations: list[StyleViolation] = []
        violations.extend(self._check_naming(code, profile))
        violations.extend(self._check_imports(code, profile))
        corrected = self._auto_correct(code, violations, profile)
        score = max(0.0, round(100.0 - len(violations) * 7.5, 2))
        return StyleCheckResult(violations=violations, score=score, corrected_code=corrected)

    def _check_naming(self, code: str, profile: StyleProfile) -> list[StyleViolation]:
        out: list[StyleViolation] = []
        lines = code.splitlines()
        if profile.naming_convention == "snake_case":
            pattern = re.compile(r"\bdef\s+([a-zA-Z][a-zA-Z0-9]*)\s*\(")
            for i, line in enumerate(lines, start=1):
                m = pattern.search(line)
                if m and "_" not in m.group(1) and m.group(1).lower() != m.group(1):
                    out.append(StyleViolation(rule="naming", line=i, message=f"Function `{m.group(1)}` should be snake_case", severity="medium"))
        return out

    def _check_imports(self, code: str, profile: StyleProfile) -> list[StyleViolation]:
        out: list[StyleViolation] = []
        if profile.import_style == "grouped":
            lines = code.splitlines()
            for i in range(len(lines) - 1):
                if lines[i].startswith("import ") and lines[i + 1].startswith("from "):
                    out.append(StyleViolation(rule="imports", line=i + 2, message="Expected blank line between import groups", severity="low"))
        return out

    def _auto_correct(self, code: str, violations: list[StyleViolation], profile: StyleProfile) -> str:
        fixed = code
        if profile.naming_convention == "snake_case":
            fixed = re.sub(r"def\s+([a-z]+)([A-Z])", lambda m: f"def {m.group(1)}_{m.group(2).lower()}", fixed)
        return fixed
