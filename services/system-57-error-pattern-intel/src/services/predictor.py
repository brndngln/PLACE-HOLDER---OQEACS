from __future__ import annotations

import ast

from src.models import ErrorReport


class ErrorPredictor:
    def predict_errors(self, code: str, language: str = "python") -> ErrorReport:
        predicted: list[str] = []
        fixes: list[str] = []

        if language == "python":
            predicted.extend(self._python_ast_checks(code))
        if "except:" in code or "except Exception" in code:
            predicted.append("Overly broad exception handling may hide failures")
            fixes.append("Catch specific exceptions and re-raise unknown failures")
        if "def " in code and "=[]" in code:
            predicted.append("Mutable default argument can leak state")
            fixes.append("Use None defaults and initialize inside function")
        if "open(" in code and "with open(" not in code:
            predicted.append("File handle might not be closed")
            fixes.append("Use context manager `with open(...)`")

        risk = min(1.0, round(0.12 + 0.12 * len(predicted), 3))
        return ErrorReport(code=code, language=language, predicted_errors=predicted, risk_score=risk, suggested_fixes=sorted(set(fixes)))

    @staticmethod
    def _python_ast_checks(code: str) -> list[str]:
        findings: list[str] = []
        try:
            tree = ast.parse(code)
        except Exception:
            return ["Syntax error likely"]

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
                findings.append("Use of eval introduces security and runtime risk")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "json_data":
                findings.append("Potential hallucinated API call: json_data")
        return findings
