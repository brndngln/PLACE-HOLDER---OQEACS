from __future__ import annotations

from src.models import AnalysisResult
from src.services.go_analyzer import GoAnalyzer
from src.services.python_analyzer import PythonAnalyzer
from src.services.sql_analyzer import SQLAnalyzer
from src.services.typescript_analyzer import TypeScriptAnalyzer


class AnalyzerRegistry:
    def __init__(self) -> None:
        self._registry = {
            "python": PythonAnalyzer(),
            "typescript": TypeScriptAnalyzer(),
            "ts": TypeScriptAnalyzer(),
            "sql": SQLAnalyzer(),
            "go": GoAnalyzer(),
        }

    def get_analyzer(self, language: str):
        return self._registry.get(language.lower())

    def analyze(self, code: str, language: str) -> AnalysisResult:
        analyzer = self.get_analyzer(language)
        if analyzer is None:
            return AnalysisResult(language=language, score=100.0, summary="Language not yet supported")
        issues = analyzer.analyze(code)
        score = max(0.0, round(100 - len(issues) * 10, 2))
        return AnalysisResult(language=language, issues=issues, score=score, summary=f"Found {len(issues)} issue(s)")
