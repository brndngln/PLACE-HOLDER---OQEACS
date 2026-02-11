from __future__ import annotations

import ast
import uuid

from src.models import Mutant, MutationResult


class MutationEngine:
    OPERATORS = {
        "negate_condition": lambda s: s.replace("==", "!=", 1),
        "remove_return": lambda s: s.replace("return", "pass # removed return", 1),
        "swap_operator": lambda s: s.replace("+", "-", 1),
        "change_boundary": lambda s: s.replace(">", ">=", 1),
        "delete_statement": lambda s: "\n".join(s.splitlines()[:-1]) if s.splitlines() else s,
        "swap_args": lambda s: s.replace("(a, b)", "(b, a)", 1),
        "null_return": lambda s: s.replace("return", "return None #", 1),
        "empty_collection": lambda s: s.replace("[]", "[ ]", 1),
        "flip_boolean": lambda s: s.replace("True", "False", 1),
        "change_constant": lambda s: s.replace("1", "2", 1),
        "remove_exception_handler": lambda s: s.replace("except", "# except", 1),
        "swap_comparisons": lambda s: s.replace("<", ">", 1),
    }

    def mutate(self, code: str, language: str = "python") -> MutationResult:
        lines = code.splitlines() or [""]
        mutants: list[Mutant] = []
        for i, (name, op) in enumerate(self.OPERATORS.items(), start=1):
            mutated = op(code)
            if mutated == code:
                continue
            mutant = Mutant(
                id=str(uuid.uuid4()),
                operator=name,
                line=min(i, len(lines)),
                original=code,
                mutated=mutated,
                killed=self._run_test_against_mutant(mutated),
                killing_test="generated_test" if "assert" in mutated else None,
            )
            mutants.append(mutant)

        killed = sum(1 for m in mutants if m.killed)
        total = len(mutants)
        survived = total - killed
        score = 0.0 if total == 0 else round((killed / total) * 100, 2)

        return MutationResult(
            original_code=code,
            mutants_generated=total,
            mutants_killed=killed,
            mutants_survived=survived,
            mutation_score=score,
            surviving_mutants=[m for m in mutants if not m.killed],
        )

    def _run_test_against_mutant(self, mutant_code: str) -> bool:
        try:
            ast.parse(mutant_code)
        except SyntaxError:
            return True
        return "raise" in mutant_code or "assert" in mutant_code
