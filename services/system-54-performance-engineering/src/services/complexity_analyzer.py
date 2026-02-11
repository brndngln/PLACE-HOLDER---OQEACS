from __future__ import annotations

import ast

from src.models import ComplexityReport, FunctionComplexity, Issue


class ComplexityAnalyzer:
    def analyze_complexity(self, code: str, language: str = "python") -> ComplexityReport:
        if language != "python":
            return ComplexityReport(language=language, score=80.0)

        tree = ast.parse(code or "")
        funcs: list[FunctionComplexity] = []
        issues: list[Issue] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                cyclomatic = 1 + sum(isinstance(n, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.BoolOp)) for n in ast.walk(node))
                cognitive = sum(isinstance(n, (ast.If, ast.For, ast.While)) for n in ast.walk(node))
                funcs.append(FunctionComplexity(function_name=node.name, line=node.lineno, cyclomatic=cyclomatic, cognitive=cognitive))
                if cyclomatic > 10:
                    issues.append(Issue(category="complexity", severity="high", line=node.lineno, message=f"{node.name} cyclomatic complexity is {cyclomatic}", suggestion="Split function into smaller units"))

        if "for" in code and code.count("for") > 1:
            issues.append(Issue(category="algorithm", severity="medium", line=1, message="Nested loops may cause O(n^2)", suggestion="Consider indexing or hashing"))

        score = max(0.0, round(100 - len(issues) * 10 - sum(max(0, f.cyclomatic - 5) for f in funcs) * 1.5, 2))
        return ComplexityReport(language="python", functions=funcs, issues=issues, score=score)
