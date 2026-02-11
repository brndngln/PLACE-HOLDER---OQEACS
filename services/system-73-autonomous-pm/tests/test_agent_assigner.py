from __future__ import annotations

from src.models import Story
from src.services.agent_assigner import AgentAssigner


def _story(title: str, complexity: str = "medium") -> Story:
    return Story(id=title, title=title, description=title, acceptance_criteria=[], estimated_complexity=complexity, assigned_agent="", status="todo")


def test_assign_returns_mapping() -> None:
    out = AgentAssigner().assign([_story("a"), _story("b")])
    assert len(out) == 2


def test_security_story_to_reviewer() -> None:
    s = _story("security hardening")
    out = AgentAssigner().assign([s])
    assert out[s.id] == "reviewer"


def test_high_complexity_to_architect() -> None:
    s = _story("core", "high")
    out = AgentAssigner().assign([s])
    assert out[s.id] == "architect"
