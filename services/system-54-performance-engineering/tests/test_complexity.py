from __future__ import annotations

from src.services.complexity_analyzer import ComplexityAnalyzer


def test_simple_function_low_complexity() -> None:
    report = ComplexityAnalyzer().analyze_complexity("def a():\n    return 1\n", "python")
    assert report.score > 80


def test_nested_branches_raise_complexity() -> None:
    code = "def x(a):\n    if a:\n        for i in range(3):\n            if i:\n                pass\n"
    report = ComplexityAnalyzer().analyze_complexity(code, "python")
    assert len(report.functions) == 1


def test_non_python_supported() -> None:
    report = ComplexityAnalyzer().analyze_complexity("function x(){}", "typescript")
    assert report.language == "typescript"


def test_detect_nested_loop_issue() -> None:
    code = "def x(l):\n    for a in l:\n        for b in l:\n            print(a,b)\n"
    report = ComplexityAnalyzer().analyze_complexity(code, "python")
    assert any(i.category == "algorithm" for i in report.issues)


def test_score_decreases_with_issues() -> None:
    code = "def x(a):\n    if a:\n        if a>1:\n            if a>2:\n                if a>3:\n                    return a\n"
    report = ComplexityAnalyzer().analyze_complexity(code, "python")
    assert report.score <= 100


def test_function_count() -> None:
    code = "def a():\n    return 1\n\ndef b():\n    return 2\n"
    report = ComplexityAnalyzer().analyze_complexity(code, "python")
    assert len(report.functions) == 2
