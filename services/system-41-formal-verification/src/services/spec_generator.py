"""Spec generation — uses LLM to generate formal specifications from source code."""
from __future__ import annotations

import uuid

import httpx
import structlog

from src.config import Settings
from src.models import SpecGenerationRequest, SpecGenerationResult, VerificationTool

logger = structlog.get_logger()

SPEC_PROMPTS: dict[str, str] = {
    "crosshair": (
        "Generate Python type annotations and crosshair-compatible contracts "
        "(using `assert` statements as preconditions and postconditions) for the following Python code. "
        "Add `@hypothesis.given` style property-based test annotations where appropriate. "
        "Return ONLY the annotated Python code, no explanation.\n\n"
    ),
    "tla_plus": (
        "Generate a TLA+ specification for the following distributed protocol or algorithm. "
        "Include VARIABLE declarations, Init and Next state predicates, and key safety/liveness "
        "properties as THEOREM statements. Return ONLY the TLA+ spec, no explanation.\n\n"
    ),
    "dafny": (
        "Generate a Dafny specification for the following algorithm. Include method contracts "
        "(requires/ensures clauses), loop invariants, and termination measures (decreases clauses). "
        "Return ONLY the Dafny code, no explanation.\n\n"
    ),
    "cbmc": (
        "Generate CBMC assertions and __CPROVER_assume statements for the following C code. "
        "Add bounds checks, pointer validity assertions, and loop unwinding pragmas. "
        "Return ONLY the annotated C code, no explanation.\n\n"
    ),
    "spin": (
        "Generate a PROMELA model for the following concurrent protocol. Include process types, "
        "channel declarations, and LTL properties for deadlock freedom and liveness. "
        "Return ONLY the PROMELA code, no explanation.\n\n"
    ),
    "kani": (
        "Generate Kani proof harnesses for the following Rust code. Include #[kani::proof] "
        "annotated functions with kani::any() for symbolic inputs and assert! for properties. "
        "Return ONLY the Rust code with harnesses, no explanation.\n\n"
    ),
    "alloy": (
        "Generate an Alloy specification for the following data model or constraints. "
        "Include signatures, facts, predicates, and assert statements. "
        "Return ONLY the Alloy spec, no explanation.\n\n"
    ),
}


class SpecGenerator:
    """Generate formal specifications from source code using LLM."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate(self, request: SpecGenerationRequest) -> SpecGenerationResult:
        """Generate a formal spec for the given source code."""
        result_id = str(uuid.uuid4())
        target = request.target_spec.value

        prompt_prefix = SPEC_PROMPTS.get(target, SPEC_PROMPTS["crosshair"])
        full_prompt = prompt_prefix

        if request.description:
            full_prompt += f"Description: {request.description}\n\n"

        full_prompt += f"Source ({request.language}):\n```\n{request.source_code}\n```"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.settings.LITELLM_URL}/v1/chat/completions",
                    json={
                        "model": "qwen2.5-72b",
                        "messages": [{"role": "user", "content": full_prompt}],
                        "max_tokens": 4096,
                        "temperature": 0.1,
                    },
                )
                resp.raise_for_status()
                generated = resp.json()["choices"][0]["message"]["content"]

            generated_clean = generated.strip()
            if generated_clean.startswith("```"):
                lines = generated_clean.splitlines()
                generated_clean = "\n".join(lines[1:-1]) if len(lines) > 2 else generated_clean

            annotations = self._extract_annotations(generated_clean, target)

            logger.info(
                "spec_generated",
                result_id=result_id,
                target=target,
                annotations=len(annotations),
            )

            return SpecGenerationResult(
                id=result_id,
                original_language=request.language,
                target_spec=request.target_spec,
                generated_spec=generated_clean,
                annotations=annotations,
                confidence=0.85,
            )

        except Exception as exc:
            logger.error("spec_generation_failed", error=str(exc))
            return SpecGenerationResult(
                id=result_id,
                original_language=request.language,
                target_spec=request.target_spec,
                generated_spec=f"# Generation failed: {exc}",
                annotations=[],
                confidence=0.0,
            )

    def _extract_annotations(self, spec: str, target: str) -> list[str]:
        """Extract notable annotations from the generated spec."""
        annotations: list[str] = []
        keywords: dict[str, list[str]] = {
            "crosshair": ["assert ", "# pre:", "# post:", "@hypothesis"],
            "tla_plus": ["THEOREM", "INVARIANT", "PROPERTY", "Safety", "Liveness"],
            "dafny": ["requires", "ensures", "invariant", "decreases"],
            "cbmc": ["__CPROVER_assert", "__CPROVER_assume", "assert("],
            "spin": ["ltl ", "assert(", "progress ", "accept "],
            "kani": ["#[kani::proof]", "kani::any()", "assert!"],
            "alloy": ["assert ", "fact ", "pred ", "check "],
        }

        target_keywords = keywords.get(target, [])
        for line in spec.splitlines():
            stripped = line.strip()
            for kw in target_keywords:
                if kw in stripped:
                    annotations.append(stripped[:120])
                    break

        return annotations
