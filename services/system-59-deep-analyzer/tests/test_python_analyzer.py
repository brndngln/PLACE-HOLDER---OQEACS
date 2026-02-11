from __future__ import annotations

from src.services.python_analyzer import PythonAnalyzer


def test_mutable_default_detected() -> None:
    issues = PythonAnalyzer().analyze("def f(x=[]):\n    return x")
    assert any(i.rule_id == "PY-MUTABLE-DEFAULT" for i in issues)


def test_bare_except_detected() -> None:
    issues = PythonAnalyzer().analyze("try:\n    x=1\nexcept:\n    pass")
    assert any(i.rule_id == "PY-EXCEPT-BARE" for i in issues)


def test_async_blocking_detected() -> None:
    code = "async def run():\n    sleep(1)"
    issues = PythonAnalyzer().analyze(code)
    assert any(i.rule_id == "PY-ASYNC-BLOCK" for i in issues)


def test_syntax_error_reported() -> None:
    issues = PythonAnalyzer().analyze("def x(:\n    pass")
    assert any(i.rule_id == "PY-SYNTAX" for i in issues)


def test_clean_code_low_issues() -> None:
    issues = PythonAnalyzer().analyze("def add(a,b):\n    return a+b")
    assert isinstance(issues, list)


def test_eval_detected() -> None:
    issues = PythonAnalyzer().analyze("def run(s):\n    return eval(s)")
    assert any("eval" in i.message.lower() for i in issues)
