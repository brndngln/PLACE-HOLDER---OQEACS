from __future__ import annotations

from src.models import PromptOptimizeRequest
from src.services.optimizer import PromptOptimizer


def test_reduces_tokens() -> None:
    req = PromptOptimizeRequest(current_prompt="please carefully do this in a detailed manner", task_description="x", optimization_goal="cost")
    out = PromptOptimizer().optimize(req)
    assert out.token_reduction_pct >= 0


def test_quality_estimate_range() -> None:
    req = PromptOptimizeRequest(current_prompt="x", task_description="x", optimization_goal="quality")
    out = PromptOptimizer().optimize(req)
    assert 0 <= out.quality_estimate <= 1


def test_returns_optimized_string() -> None:
    req = PromptOptimizeRequest(current_prompt="very very important", task_description="x", optimization_goal="all")
    out = PromptOptimizer().optimize(req)
    assert isinstance(out.optimized, str)
