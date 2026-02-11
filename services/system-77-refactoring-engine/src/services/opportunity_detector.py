from __future__ import annotations

import re
import uuid

from src.models import RefactoringOpportunity


class OpportunityDetector:
    def scan(self, code: str, language: str = "python") -> list[RefactoringOpportunity]:
        opps: list[RefactoringOpportunity] = []
        lines = code.splitlines()

        if re.search(r"\bimport\s+\w+\b", code) and "unused" in code.lower():
            opps.append(self._op("dead_code", "Potential unused import/dead path"))
        if self._detect_duplication(lines):
            opps.append(self._op("duplication", "Repeated code blocks detected"))
        if self._long_method(lines):
            opps.append(self._op("extract_method", "Long function body; consider extraction"))
        if code.count("if ") >= 4:
            opps.append(self._op("simplify_conditional", "Complex nested conditionals"))
        if code.count("class ") == 1 and code.count("def ") > 10:
            opps.append(self._op("extract_class", "Potential god class"))
        return opps

    @staticmethod
    def _op(kind: str, description: str) -> RefactoringOpportunity:
        return RefactoringOpportunity(id=str(uuid.uuid4()), file_path="inline", type=kind, description=description, risk="medium", estimated_effort="medium")

    @staticmethod
    def _detect_duplication(lines: list[str]) -> bool:
        normalized_lines = [line.strip() for line in lines if line.strip()]
        if len(normalized_lines) != len(set(normalized_lines)):
            return True
        chunks = ["\n".join(lines[i : i + 3]).strip() for i in range(max(0, len(lines) - 2))]
        non_empty = [c for c in chunks if c]
        return len(non_empty) != len(set(non_empty))

    @staticmethod
    def _long_method(lines: list[str]) -> bool:
        return len(lines) > 50
