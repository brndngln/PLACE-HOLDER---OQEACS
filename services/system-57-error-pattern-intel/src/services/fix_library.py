from __future__ import annotations

from src.models import FixTemplate


class FixLibrary:
    def __init__(self) -> None:
        self._store: dict[str, FixTemplate] = {}
        self._stats: dict[str, int] = {"served": 0, "stored": 0}

    def get_fix(self, pattern_id: str) -> FixTemplate | None:
        fix = self._store.get(pattern_id)
        if fix:
            self._stats["served"] += 1
        return fix

    def store_fix(self, pattern_id: str, fix: FixTemplate) -> None:
        self._store[pattern_id] = fix
        self._stats["stored"] += 1

    def auto_generate_fix(self, error_pattern: str) -> FixTemplate:
        before = "# failing code"
        after = "# fixed code with validation"
        desc = f"Apply guard clauses and validate inputs for pattern: {error_pattern}"
        return FixTemplate(pattern_id=error_pattern, fix_description=desc, code_before=before, code_after=after, confidence=0.6)

    def stats(self) -> dict[str, int]:
        return dict(self._stats)
