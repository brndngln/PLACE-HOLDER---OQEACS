from __future__ import annotations

from src.models import GeneratedProject


class RefinementEngine:
    def refine(self, project: GeneratedProject, instruction: str) -> GeneratedProject:
        project.files["README.md"] += f"\n## Refinement\n- {instruction}\n"
        if "logging" in instruction.lower() and "app/main.py" in project.files:
            project.files["app/main.py"] = "import logging\n" + project.files["app/main.py"]
        project.total_lines = sum(len(v.splitlines()) for v in project.files.values())
        return project
