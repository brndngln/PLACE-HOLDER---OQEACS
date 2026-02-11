from __future__ import annotations

from src.models import PRD
from src.services.task_decomposer import TaskDecomposer


def test_decompose_basic() -> None:
    prd = PRD(title="A", description="B", requirements=["Build API"], acceptance_criteria=[])
    epics = TaskDecomposer().decompose(prd)
    assert len(epics) == 1


def test_story_created() -> None:
    prd = PRD(title="A", description="B", requirements=["Build UI"], acceptance_criteria=[])
    epics = TaskDecomposer().decompose(prd)
    assert epics[0].stories


def test_complexity_high_for_long_req() -> None:
    req = "build a complete distributed system with many bounded contexts and orchestration logic"
    prd = PRD(title="A", description="B", requirements=[req], acceptance_criteria=[])
    epics = TaskDecomposer().decompose(prd)
    assert epics[0].stories[0].estimated_complexity in {"high", "medium"}


def test_points_positive() -> None:
    prd = PRD(title="A", description="B", requirements=["x"], acceptance_criteria=[])
    epics = TaskDecomposer().decompose(prd)
    assert epics[0].estimated_points > 0
