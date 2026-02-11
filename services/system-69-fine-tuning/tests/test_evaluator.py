from __future__ import annotations

from src.services.evaluator import ModelEvaluator


def test_evaluate_returns_results() -> None:
    out = ModelEvaluator().evaluate("model", ["HumanEval"])
    assert len(out) == 1


def test_improvement_computed() -> None:
    out = ModelEvaluator().evaluate("model", ["HumanEval"])
    assert out[0].improvement_pct >= 0


def test_multiple_benchmarks() -> None:
    out = ModelEvaluator().evaluate("model", ["HumanEval", "CustomCoding"])
    assert len(out) == 2
