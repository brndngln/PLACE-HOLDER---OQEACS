from __future__ import annotations

from src.models import ProjectBlueprint
from src.services.code_orchestrator import CodeOrchestrator


def _bp() -> ProjectBlueprint:
    return ProjectBlueprint(name="app", structure={}, services=["api"], database_schema="", api_endpoints=["/health"], estimated_files=4)


def test_generate_project_files() -> None:
    out = CodeOrchestrator().generate_project(_bp())
    assert out.total_files >= 1


def test_generate_project_lines() -> None:
    out = CodeOrchestrator().generate_project(_bp())
    assert out.total_lines > 0


def test_compose_present() -> None:
    out = CodeOrchestrator().generate_project(_bp())
    assert "services:" in out.docker_compose
