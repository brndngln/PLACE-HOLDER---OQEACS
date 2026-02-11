"""Code meaning extraction using heuristic + LLM augmentation."""

from __future__ import annotations

import json
import re

import httpx

from src.config import settings
from src.models import CodeMeaning


class MeaningExtractor:
    """Extracts semantic intent and implicit contracts from code snippets."""

    SIDE_EFFECT_PATTERNS: dict[str, str] = {
        r"\bopen\(": "File I/O",
        r"\brequests\.(get|post|put|delete)\b": "Network I/O",
        r"\bhttpx\.(get|post|put|delete)\b": "Network I/O",
        r"\bexecute\(" : "Database write/query",
        r"\bredis\.": "Cache/queue mutation",
        r"\bprint\(" : "Stdout side effect",
        r"\blogger\.": "Logging side effect",
    }

    def extract_meaning(self, code: str, language: str, context: str = "") -> CodeMeaning:
        side_effects = self._identify_side_effects(code)
        invariants = self._extract_invariants(code)
        implicit = self._find_implicit_contracts(code, context)

        summary = self._heuristic_summary(code, language)
        purpose = f"Implements {language} logic for the provided task context." if context else f"Implements {language} business logic."

        llm = self._llm_enrich(code=code, language=language, context=context)
        if llm:
            summary = llm.get("summary", summary)
            purpose = llm.get("purpose", purpose)
            side_effects = llm.get("side_effects", side_effects)
            invariants = llm.get("invariants", invariants)
            implicit = llm.get("implicit_contracts", implicit)

        return CodeMeaning(
            summary=summary,
            purpose=purpose,
            side_effects=side_effects,
            invariants=invariants,
            implicit_contracts=implicit,
            complexity_assessment=self._complexity_assessment(code),
        )

    def _identify_side_effects(self, code: str) -> list[str]:
        effects: list[str] = []
        for pattern, label in self.SIDE_EFFECT_PATTERNS.items():
            if re.search(pattern, code):
                effects.append(label)
        return sorted(set(effects))

    @staticmethod
    def _extract_invariants(code: str) -> list[str]:
        invariants: list[str] = []
        if "if " in code and "raise" in code:
            invariants.append("Input validation guards exist before core logic")
        if "for " in code and "append(" in code:
            invariants.append("Loop accumulates results in order")
        if "return" in code:
            invariants.append("Function always returns a value on happy path")
        return invariants

    @staticmethod
    def _find_implicit_contracts(code: str, context: str) -> list[str]:
        contracts: list[str] = []
        if "sorted(" in code or "bisect" in code:
            contracts.append("Assumes sequence ordering semantics")
        if "json" in code.lower():
            contracts.append("Assumes JSON-serializable data structures")
        if "id" in code and "None" in code:
            contracts.append("Assumes nullable identifiers are handled")
        if context:
            contracts.append("Must remain compatible with surrounding system context")
        return contracts

    @staticmethod
    def _heuristic_summary(code: str, language: str) -> str:
        lines = [line.strip() for line in code.splitlines() if line.strip()]
        if not lines:
            return "Empty code sample"
        if language == "python" and lines[0].startswith("def "):
            fn = lines[0].split("def ", 1)[1].split("(", 1)[0]
            return f"Defines function `{fn}` and supporting logic."
        if language == "typescript" and "export" in code:
            return "Exports TypeScript module logic and typed interfaces."
        return f"Contains {len(lines)} lines of executable {language} code."

    @staticmethod
    def _complexity_assessment(code: str) -> str:
        branches = sum(code.count(k) for k in [" if ", " for ", " while ", " match ", " case "])
        if branches <= 2:
            return "Low complexity"
        if branches <= 6:
            return "Moderate complexity"
        return "High complexity; consider decomposition"

    def _llm_enrich(self, *, code: str, language: str, context: str) -> dict[str, object] | None:
        prompt = (
            "Return strict JSON with keys summary,purpose,side_effects,invariants,implicit_contracts. "
            f"Analyze this {language} code with context '{context}':\n```{language}\n{code[:3500]}\n```"
        )
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(
                    f"{settings.LITELLM_URL}/v1/chat/completions",
                    json={
                        "model": settings.DEFAULT_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed
        except Exception:
            return None
        return None
