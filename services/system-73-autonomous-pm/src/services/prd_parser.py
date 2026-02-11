from __future__ import annotations

from src.models import PRD


class PRDParser:
    def parse(self, prd_text: str) -> PRD:
        lines = [x.strip() for x in prd_text.splitlines() if x.strip()]
        title = lines[0] if lines else "Untitled Project"
        reqs = [l[2:].strip() for l in lines if l.startswith("- ")]
        criteria = [l.split(":", 1)[1].strip() for l in lines if l.lower().startswith("acceptance:")]
        return PRD(title=title, description=prd_text, requirements=reqs, acceptance_criteria=criteria)
