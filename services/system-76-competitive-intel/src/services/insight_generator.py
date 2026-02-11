from __future__ import annotations

from src.models import CompetitiveInsight, ImplementationExample


class InsightGenerator:
    def get_insights(self, topic: str) -> CompetitiveInsight:
        implementations = [
            ImplementationExample(project="tiangolo/fastapi", language="python", approach="ASGI-first API design", pros=["fast", "typed"], cons=["ecosystem variance"], stars=80000, source_url="https://github.com/tiangolo/fastapi"),
            ImplementationExample(project="nestjs/nest", language="typescript", approach="modular DI architecture", pros=["enterprise patterns"], cons=["boilerplate"], stars=60000, source_url="https://github.com/nestjs/nest"),
        ]
        best = ["Prefer explicit contracts", "Automate verification in CI", "Use typed DTOs"]
        trends = ["Shift toward AI-assisted code review", "More typed APIs", "Runtime policy enforcement"]
        return CompetitiveInsight(topic=topic, implementations=implementations, best_practices=best, trends=trends)
