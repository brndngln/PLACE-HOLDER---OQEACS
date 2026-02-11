from __future__ import annotations

from src.models import DependencyRule
from src.services.dependency_checker import DependencyChecker


def test_forbidden_dependency_detected() -> None:
    rules = [DependencyRule(source_pattern="frontend", forbidden_pattern="backend", reason="boundary")]
    imports = {"frontend/ui.py": ["backend.service"]}
    out = DependencyChecker().check_dependencies(rules, imports)
    assert len(out) == 1


def test_no_violation_when_allowed() -> None:
    rules = [DependencyRule(source_pattern="frontend", forbidden_pattern="backend", reason="boundary")]
    imports = {"frontend/ui.py": ["frontend.theme"]}
    out = DependencyChecker().check_dependencies(rules, imports)
    assert out == []


def test_cycle_detected() -> None:
    imports = {"a": ["b"], "b": ["a"]}
    cycles = DependencyChecker().detect_circular_dependencies(imports)
    assert len(cycles) >= 1


def test_cycle_none() -> None:
    imports = {"a": ["b"], "b": []}
    cycles = DependencyChecker().detect_circular_dependencies(imports)
    assert cycles == []


def test_multiple_rules() -> None:
    rules = [
        DependencyRule(source_pattern="frontend", forbidden_pattern="backend", reason="boundary"),
        DependencyRule(source_pattern="api", forbidden_pattern="infra", reason="layering"),
    ]
    imports = {"api/routes.py": ["infra.db"], "frontend/x.py": ["backend.z"]}
    out = DependencyChecker().check_dependencies(rules, imports)
    assert len(out) == 2
