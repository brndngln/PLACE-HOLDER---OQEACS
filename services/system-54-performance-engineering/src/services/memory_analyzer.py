from __future__ import annotations

from src.models import MemoryLeakPattern


class MemoryAnalyzer:
    def detect_leaks(self, code: str) -> list[MemoryLeakPattern]:
        findings: list[MemoryLeakPattern] = []
        lines = code.splitlines()
        for i, line in enumerate(lines, start=1):
            if "open(" in line and "with open(" not in line:
                findings.append(MemoryLeakPattern(line=i, pattern="unclosed_file", suggestion="Use context manager `with open(...)`"))
            if "while True" in line and "break" not in "\n".join(lines[i : i + 8]):
                findings.append(MemoryLeakPattern(line=i, pattern="unbounded_loop", suggestion="Add exit condition"))
            if "append(" in line and "for" in "\n".join(lines[max(0, i - 4) : i]):
                findings.append(MemoryLeakPattern(line=i, pattern="growing_collection", suggestion="Limit buffer size or stream results"))
        return findings
