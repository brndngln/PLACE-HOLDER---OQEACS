from __future__ import annotations

from src.models import CollectRequest, TrainingDataEntry


class DataCollector:
    def collect(self, request: CollectRequest) -> list[TrainingDataEntry]:
        samples = [
            TrainingDataEntry(
                instruction="Refactor function for readability",
                input_text="def x(a,b):return a+b",
                output_text="def add(a: int, b: int) -> int:\n    return a + b",
                quality_score=0.91,
                source=request.source,
                language="python",
                task_type="refactor",
            ),
            TrainingDataEntry(
                instruction="Add validation",
                input_text="user = payload['user']",
                output_text="user = payload.get('user')\nif user is None:\n    raise ValueError('user is required')",
                quality_score=0.89,
                source=request.source,
                language="python",
                task_type="bug_fix",
            ),
        ]
        return [s for s in samples if s.quality_score >= 0.8]
