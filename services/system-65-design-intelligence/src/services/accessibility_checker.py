from __future__ import annotations

import re

from src.models import AccessibilityReport


class AccessibilityChecker:
    def check(self, code: str) -> AccessibilityReport:
        violations: list[str] = []
        suggestions: list[str] = []

        if "<img" in code and "alt=" not in code:
            violations.append("Missing alt text on image")
            suggestions.append("Add descriptive alt attributes")
        if "onClick" in code and "onKeyDown" not in code and "button" not in code:
            violations.append("Clickable non-semantic element without keyboard handler")
            suggestions.append("Use semantic button or add keyboard interaction")
        if re.search(r"color\s*:\s*#([0-9a-fA-F]{3,6})", code) and "background" not in code:
            suggestions.append("Verify contrast ratio against background")
        if "aria-" not in code:
            suggestions.append("Add ARIA attributes for assistive technologies")

        score = max(0.0, round(100 - len(violations) * 20 - max(0, len(suggestions) - len(violations)) * 5, 2))
        return AccessibilityReport(score=score, violations=violations, suggestions=suggestions)
