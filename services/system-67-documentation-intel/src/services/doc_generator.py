from __future__ import annotations

import re

from src.models import DiagramSpec, DocGenerationRequest, GeneratedDoc
from src.services.diagram_generator import DiagramGenerator


class DocGenerator:
    def generate(self, request: DocGenerationRequest) -> GeneratedDoc:
        if request.doc_type == "api":
            sections = ["Overview", "Endpoints", "Examples", "Error Handling"]
            content = self._api_doc(request.code)
        elif request.doc_type == "readme":
            sections = ["Overview", "Setup", "Usage", "Development", "License"]
            content = self._readme_doc(request.code)
        elif request.doc_type == "architecture":
            sections = ["Components", "Data Flow", "Boundaries"]
            content = self._architecture_doc(request.code)
        elif request.doc_type == "onboarding":
            sections = ["Prerequisites", "Local Run", "Test", "Troubleshooting"]
            content = self._onboarding_doc(request.code)
        else:
            sections = ["Changes", "Breaking Changes", "Migration"]
            content = self._changelog_doc(request.code)

        diagrams = [DiagramGenerator().generate_architecture_from_code(request.code)]
        return GeneratedDoc(content=content, sections=sections, diagrams=diagrams)

    def _api_doc(self, code: str) -> str:
        routes = re.findall(r"@(app|router)\.(get|post|put|delete)\(['\"]([^'\"]+)", code)
        lines = ["# API Documentation", ""]
        if not routes:
            lines.append("No routes discovered from code input.")
        else:
            for _, method, path in routes:
                lines.append(f"- `{method.upper()} {path}`")
        lines.extend(["", "## Example", "```bash", "curl http://localhost:8000/health", "```"])
        return "\n".join(lines)

    def _readme_doc(self, code: str) -> str:
        return "\n".join(["# Project", "", "## What it does", "Auto-generated from source.", "", "## Key Functions", code[:500]])

    def _architecture_doc(self, code: str) -> str:
        return "\n".join(["# Architecture", "", "```mermaid", "graph TD", "  Client-->API", "  API-->DB", "```", ""])

    def _onboarding_doc(self, code: str) -> str:
        return "\n".join(["# Onboarding", "", "1. Install dependencies", "2. Run tests", "3. Start service"])

    def _changelog_doc(self, code: str) -> str:
        return "\n".join(["# Changelog", "", "- Added generated documentation support"])
