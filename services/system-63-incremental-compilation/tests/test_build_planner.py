from __future__ import annotations

from src.models import DependencyGraph
from src.services.build_planner import BuildPlanner


def test_plan_build_transitive() -> None:
    graph = DependencyGraph(nodes=["a.py", "b.py", "c.py"], edges=[("b.py", "a.py"), ("c.py", "b.py")])
    plan = BuildPlanner().plan_build(["a.py"], graph)
    assert "c.py" in plan.files_to_rebuild


def test_cache_ratio() -> None:
    graph = DependencyGraph(nodes=["a.py", "b.py"], edges=[])
    plan = BuildPlanner().plan_build(["a.py"], graph)
    assert 0 <= plan.cache_hit_ratio <= 1


def test_empty_graph() -> None:
    graph = DependencyGraph(nodes=[], edges=[])
    plan = BuildPlanner().plan_build([], graph)
    assert plan.files_to_rebuild == []
