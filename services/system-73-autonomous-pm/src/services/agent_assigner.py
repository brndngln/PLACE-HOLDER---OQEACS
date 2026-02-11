from __future__ import annotations

from src.models import Story


class AgentAssigner:
    def assign(self, stories: list[Story]) -> dict[str, str]:
        assignments: dict[str, str] = {}
        pool = ["architect", "developer", "tester", "reviewer", "optimizer"]
        for i, story in enumerate(stories):
            if "security" in story.title.lower() or "auth" in story.description.lower():
                agent = "reviewer"
            elif story.estimated_complexity == "high":
                agent = "architect"
            else:
                agent = pool[i % len(pool)]
            assignments[story.id] = agent
            story.assigned_agent = agent
        return assignments
