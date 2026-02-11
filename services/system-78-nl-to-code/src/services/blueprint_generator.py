from __future__ import annotations

import re

from src.models import NLRequest, ProjectBlueprint


class BlueprintGenerator:
    def generate(self, request: NLRequest) -> ProjectBlueprint:
        name = self._slugify(request.description[:40]) or "generated-app"
        services = ["api"]
        if any("worker" in f.lower() for f in request.features):
            services.append("worker")
        endpoints = ["/health", "/api/v1/items", "/api/v1/items/{id}"]
        if any("auth" in x.lower() for x in request.features):
            endpoints.extend(["/api/v1/auth/login", "/api/v1/auth/register"])

        structure = {
            "app": ["main.py", "routers.py", "models.py", "services.py"],
            "tests": ["test_health.py", "test_api.py"],
            "docker": ["Dockerfile", "docker-compose.yml"],
        }
        schema = "CREATE TABLE IF NOT EXISTS items (id SERIAL PRIMARY KEY, name TEXT NOT NULL);"
        return ProjectBlueprint(name=name, structure=structure, services=services, database_schema=schema, api_endpoints=endpoints, estimated_files=10)

    @staticmethod
    def _slugify(text: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
        return clean
