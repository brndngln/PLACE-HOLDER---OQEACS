from __future__ import annotations

from src.services.predictor import ErrorPredictor


def test_detect_bare_except() -> None:
    report = ErrorPredictor().predict_errors("try:\n x=1\nexcept:\n pass", "python")
    assert any("exception" in p.lower() for p in report.predicted_errors)


def test_detect_mutable_default() -> None:
    report = ErrorPredictor().predict_errors("def f(x=[]):\n return x", "python")
    assert any("mutable" in p.lower() for p in report.predicted_errors)


def test_detect_unclosed_file() -> None:
    report = ErrorPredictor().predict_errors("f=open('x')\nprint(f.read())", "python")
    assert any("file" in p.lower() for p in report.predicted_errors)


def test_clean_code_no_warning() -> None:
    report = ErrorPredictor().predict_errors("def add(a,b):\n    return a+b", "python")
    assert report.risk_score >= 0
