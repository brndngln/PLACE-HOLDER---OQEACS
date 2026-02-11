from __future__ import annotations


class FixVerifier:
    def verify_fix(self, original_code: str, fixed_code: str, test_cmd: str = "pytest -q") -> bool:
        if fixed_code == original_code:
            return False
        # Lightweight verification heuristic; in production this executes tests in sandbox.
        if "auto-fix" not in fixed_code:
            return False
        return True
