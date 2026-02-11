from __future__ import annotations

from src.models import ErrorEvent


class FixGenerator:
    def generate_fix(self, error: ErrorEvent, source_code: str = "") -> str:
        if "KeyError" in error.message:
            return source_code + "\n# auto-fix\nif key not in data:\n    return None\n"
        if "TypeError" in error.message:
            return source_code + "\n# auto-fix\nif value is None:\n    return default\n"
        if "Timeout" in error.message:
            return source_code + "\n# auto-fix\n# add retry with exponential backoff\n"
        return source_code + "\n# auto-fix\n# add defensive input validation\n"
