"""Verification loop — the core engine that executes, tests, and regenerates code."""

from __future__ import annotations

import difflib
import json
from datetime import datetime, timezone
from textwrap import dedent

import httpx
import structlog

from src.config import Settings
from src.models import (
    ExecutionRequest,
    ExecutionResult,
    TestCase,
    VerificationResult,
)
from src.services.sandbox import SandboxExecutor
from src.services.test_runner import TestRunner

logger = structlog.get_logger()


class VerificationLoop:
    """Execute code, check test results, regenerate on failure — up to MAX_RETRIES."""

    def __init__(
        self,
        settings: Settings,
        sandbox: SandboxExecutor,
        test_runner: TestRunner,
        redis_client=None,
    ) -> None:
        self._settings = settings
        self._sandbox = sandbox
        self._test_runner = test_runner
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Core verification loop
    # ------------------------------------------------------------------

    async def verify(self, request: ExecutionRequest) -> VerificationResult:
        """THE CORE LOOP:

        1. Execute the code
        2. If it passes all tests -> return verified
        3. If it fails -> call _regenerate() with the error
        4. Try again (up to MAX_RETRIES)
        5. Track all attempts
        """
        current_code = request.code
        all_results: list[ExecutionResult] = []
        fixes_applied: list[str] = []

        # Auto-generate tests if none provided
        test_cases = request.test_cases
        if not test_cases:
            logger.info("auto_generating_tests", language=request.language)
            test_cases = await self._test_runner.auto_generate_tests(
                current_code, request.language
            )

        max_attempts = self._settings.MAX_RETRIES + 1  # first run + retries

        for attempt in range(1, max_attempts + 1):
            logger.info(
                "verification_attempt",
                attempt=attempt,
                max_attempts=max_attempts,
                language=request.language,
            )

            # --- Step 1: Execute the code ---
            exec_result = await self._sandbox.execute(
                code=current_code,
                language=request.language,
                dependencies=request.dependencies,
            )

            # --- Step 2: Run test cases ---
            if exec_result.success and test_cases:
                test_results = await self._test_runner.run_tests(
                    current_code, test_cases, request.language
                )
                exec_result.test_results = test_results
                all_passed = all(tr.passed for tr in test_results)
                if not all_passed:
                    exec_result.success = False
                    # Build a composite error message from failed tests
                    failed = [tr for tr in test_results if not tr.passed]
                    failure_msgs = [
                        f"Test '{tr.test_case.description}': expected {tr.test_case.expected_output!r}, "
                        f"got {tr.actual_output!r}"
                        + (f" (error: {tr.error})" if tr.error else "")
                        for tr in failed
                    ]
                    exec_result.stderr += "\n" + "\n".join(failure_msgs)

            all_results.append(exec_result)

            # --- Step 3: Check success ---
            if exec_result.success:
                logger.info("verification_passed", attempt=attempt)
                result = VerificationResult(
                    original_code=request.code,
                    verified_code=current_code,
                    language=request.language,
                    attempts=attempt,
                    all_results=all_results,
                    final_status="verified",
                    fixes_applied=fixes_applied,
                )
                await self._store_result(result)
                return result

            # --- Step 4: Regenerate on failure ---
            if attempt < max_attempts:
                error_context = exec_result.stderr or exec_result.stdout or "Unknown error"
                logger.info(
                    "regenerating_code",
                    attempt=attempt,
                    error_preview=error_context[:200],
                )

                new_code = await self._regenerate(
                    code=current_code,
                    error=error_context,
                    language=request.language,
                    attempt=attempt,
                )

                diff = self._diff_code(current_code, new_code)
                fixes_applied.append(f"Attempt {attempt}: {diff[:500]}")
                current_code = new_code

        # --- Exhausted all retries ---
        logger.warning(
            "verification_failed",
            total_attempts=max_attempts,
            language=request.language,
        )
        result = VerificationResult(
            original_code=request.code,
            verified_code=current_code,
            language=request.language,
            attempts=max_attempts,
            all_results=all_results,
            final_status="failed",
            fixes_applied=fixes_applied,
        )
        await self._store_result(result)
        return result

    # ------------------------------------------------------------------
    # Code regeneration via LiteLLM
    # ------------------------------------------------------------------

    async def _regenerate(
        self, code: str, error: str, language: str, attempt: int
    ) -> str:
        """Call LiteLLM with the error context to produce a fixed version of the code."""
        prompt = dedent(f"""\
            You are a senior {language} developer. The following code failed execution.
            Fix it so it runs successfully. Return ONLY the corrected code, no explanations.

            Attempt {attempt} of {self._settings.MAX_RETRIES}.

            Original code:
            ```{language}
            {code}
            ```

            Error:
            ```
            {error[:3000]}
            ```

            Return ONLY the fixed {language} code, no markdown fences:
        """)

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self._settings.LITELLM_URL}/v1/chat/completions",
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                    },
                )
                resp.raise_for_status()
                body = resp.json()

            new_code = body["choices"][0]["message"]["content"].strip()
            # Strip markdown fences if present
            if new_code.startswith("```"):
                lines = new_code.split("\n")
                lines = lines[1:]  # remove opening fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                new_code = "\n".join(lines)

            logger.info("code_regenerated", attempt=attempt, new_len=len(new_code))
            return new_code

        except Exception as exc:
            logger.error("regeneration_failed", error=str(exc), attempt=attempt)
            return code  # return original on failure

    # ------------------------------------------------------------------
    # Diff utility
    # ------------------------------------------------------------------

    @staticmethod
    def _diff_code(original: str, fixed: str) -> str:
        """Show a unified diff of what changed between attempts."""
        diff_lines = difflib.unified_diff(
            original.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile="original",
            tofile="fixed",
            lineterm="",
        )
        return "".join(diff_lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _store_result(self, result: VerificationResult) -> None:
        """Persist the verification result to Redis for retrieval and learning."""
        if self._redis is None:
            return
        try:
            key = f"exec_verify:result:{result.id}"
            payload = result.model_dump_json()
            await self._redis.set(key, payload, ex=86400 * 7)  # 7-day TTL
            logger.info("result_stored", id=result.id)
        except Exception as exc:
            logger.warning("result_store_failed", error=str(exc))
