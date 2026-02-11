from __future__ import annotations

import ast

from src.models import Issue


class PythonAnalyzer:
    def analyze(self, code: str) -> list[Issue]:
        issues: list[Issue] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return [Issue(severity="high", category="syntax", line=exc.lineno or 1, message=str(exc), suggestion="Fix syntax", rule_id="PY-SYNTAX")]

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in {"sleep", "requests"}:
                        issues.append(Issue(severity="medium", category="async", line=sub.lineno, message="Potential blocking call in async function", suggestion="Use await-compatible async client", rule_id="PY-ASYNC-BLOCK"))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                issues.append(
                    Issue(
                        severity="high",
                        category="security",
                        line=node.lineno,
                        message=f"Use of {node.func.id} can execute untrusted code",
                        suggestion="Replace dynamic evaluation with safe parsing/dispatch logic",
                        rule_id="PY-DANGEROUS-EVAL",
                    )
                )
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(Issue(severity="medium", category="exceptions", line=node.lineno, message="Bare except detected", suggestion="Catch specific exception types", rule_id="PY-EXCEPT-BARE"))
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(Issue(severity="high", category="correctness", line=node.lineno, message="Mutable default argument", suggestion="Use None default and initialize in function body", rule_id="PY-MUTABLE-DEFAULT"))
        return issues
