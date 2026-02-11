from __future__ import annotations

from src.services.mutation_engine import MutationEngine


def test_mutation_generates_mutants() -> None:
    res = MutationEngine().mutate("def add(a,b):\n    return a+b", "python")
    assert res.mutants_generated >= 1


def test_mutation_score_in_bounds() -> None:
    res = MutationEngine().mutate("print(1)", "python")
    assert 0 <= res.mutation_score <= 100


def test_surviving_mutants_list() -> None:
    res = MutationEngine().mutate("def x():\n    return 1", "python")
    assert isinstance(res.surviving_mutants, list)


def test_operator_set_size() -> None:
    assert len(MutationEngine.OPERATORS) >= 12


def test_handles_empty_code() -> None:
    res = MutationEngine().mutate("", "python")
    assert isinstance(res.mutants_generated, int)
