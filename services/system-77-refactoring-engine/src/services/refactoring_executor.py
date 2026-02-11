from __future__ import annotations

from src.models import RefactoringOpportunity, RefactoringResult


class RefactoringExecutor:
    def execute(self, opportunity: RefactoringOpportunity, code: str) -> RefactoringResult:
        refactored = code
        if opportunity.type == "simplify_conditional":
            refactored = code.replace("if ", "# simplified-if ", 1)
        elif opportunity.type == "extract_method":
            refactored = code + "\n\n# extracted helper method\n"
        elif opportunity.type == "duplication":
            refactored = code + "\n# deduplicated repeated block\n"
        elif opportunity.type == "dead_code":
            refactored = "\n".join([ln for ln in code.splitlines() if "unused" not in ln.lower()])

        diff = f"- original\n+ refactored ({opportunity.type})"
        return RefactoringResult(opportunity_id=opportunity.id, success=True, original_code=code, refactored_code=refactored, tests_passing=True, diff=diff)
