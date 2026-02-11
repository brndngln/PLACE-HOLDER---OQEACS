from __future__ import annotations


class ProjectMonitor:
    TRACKED_PROJECTS = {
        "web": ["vercel/next.js", "facebook/react", "vuejs/core"],
        "backend": ["tiangolo/fastapi", "encode/django-rest-framework", "nestjs/nest"],
        "infra": ["kubernetes/kubernetes", "hashicorp/terraform"],
    }

    def scan_project(self, project: str) -> dict:
        return {
            "project": project,
            "major_change": "unknown",
            "latest_version": "unknown",
            "pattern_shift": "none-detected",
        }

    def list_projects(self) -> list[str]:
        return [p for arr in self.TRACKED_PROJECTS.values() for p in arr]
