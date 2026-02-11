from __future__ import annotations

import hashlib

from src.models import ErrorPattern, MatchResult


class PatternMatcher:
    def __init__(self, store: dict[str, ErrorPattern]) -> None:
        self.store = store

    def compute_signature(self, error_msg: str, traceback: str = "") -> str:
        norm = " ".join((error_msg + " " + traceback).lower().split())
        for token in ["line", "file", "0x", "at "]:
            norm = norm.replace(token, "")
        return hashlib.sha256(norm.encode()).hexdigest()[:24]

    def match_error(self, error_msg: str, traceback: str = "") -> list[MatchResult]:
        sig = self.compute_signature(error_msg, traceback)
        out: list[MatchResult] = []
        for pattern in self.store.values():
            similarity = self._similarity(sig, pattern.pattern_signature)
            if similarity >= 0.45:
                out.append(
                    MatchResult(
                        pattern=pattern,
                        similarity=round(similarity, 3),
                        suggested_fix=pattern.fix_templates[0] if pattern.fix_templates else "Inspect stack trace and add guard/validation.",
                    )
                )
        out.sort(key=lambda x: x.similarity, reverse=True)
        return out

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        same = sum(1 for x, y in zip(a, b) if x == y)
        return same / max(len(a), len(b))
