from __future__ import annotations

import uuid

from src.models import Epic, PRD, Story


class TaskDecomposer:
    def decompose(self, prd: PRD) -> list[Epic]:
        stories: list[Story] = []
        for req in prd.requirements or ["Core implementation"]:
            sid = f"ST-{uuid.uuid4().hex[:6]}"
            complexity = "high" if len(req.split()) > 10 else "medium"
            stories.append(
                Story(
                    id=sid,
                    title=req[:80],
                    description=req,
                    acceptance_criteria=prd.acceptance_criteria or ["Requirement satisfied"],
                    estimated_complexity=complexity,
                    assigned_agent="developer",
                    status="todo",
                )
            )
        epic = Epic(id=f"EP-{uuid.uuid4().hex[:6]}", title=prd.title, stories=stories, estimated_points=sum(3 if s.estimated_complexity == "medium" else 5 for s in stories))
        return [epic]
