from __future__ import annotations

from src.services.project_monitor import ProjectMonitor


def test_list_projects_non_empty() -> None:
    assert ProjectMonitor().list_projects()


def test_scan_project_shape() -> None:
    out = ProjectMonitor().scan_project("tiangolo/fastapi")
    assert "project" in out


def test_tracked_projects_categories() -> None:
    assert isinstance(ProjectMonitor.TRACKED_PROJECTS, dict)
