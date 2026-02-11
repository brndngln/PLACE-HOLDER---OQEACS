from __future__ import annotations

from src.models import ProgressReport, Story


class ProgressTracker:
    def update_status(self, story: Story, status: str) -> Story:
        story.status = status
        return story

    def generate_report(self, sprint_id: str, stories: list[Story]) -> ProgressReport:
        completed = sum(1 for s in stories if s.status == "done")
        in_progress = sum(1 for s in stories if s.status == "in_progress")
        blocked = sum(1 for s in stories if s.status == "blocked")
        velocity = round(completed / max(len(stories), 1) * 100, 2)
        burndown = [{"day": i + 1, "remaining": max(len(stories) - completed - i, 0)} for i in range(5)]
        return ProgressReport(sprint_id=sprint_id, completed=completed, in_progress=in_progress, blocked=blocked, velocity=velocity, burndown=burndown)
