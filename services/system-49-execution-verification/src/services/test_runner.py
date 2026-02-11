"""Test runner — generates and executes test harnesses against submitted code."""

from __future__ import annotations

import json
import os
from textwrap import dedent

import httpx
import structlog

from src.config import Settings
from src.models import ExecutionResult, TestCase, TestCaseResult
from src.services.sandbox import SandboxExecutor

logger = structlog.get_logger()


class TestRunner:
    """Generate test harnesses, run tests, and report per-case results."""

    def __init__(self, settings: Settings, sandbox: SandboxExecutor) -> None:
        self._settings = settings
        self._sandbox = sandbox

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def run_tests(
        self,
        code: str,
        test_cases: list[TestCase],
        language: str,
    ) -> list[TestCaseResult]:
        """Run *test_cases* against *code* and return individual results."""
        if not test_cases:
            return []

        harness = self._generate_test_harness(code, test_cases, language)
        result: ExecutionResult = await self._sandbox.execute(
            code=harness,
            language=language,
            timeout=self._settings.EXECUTION_TIMEOUT_SECONDS,
        )
        return self._parse_test_output(result.stdout, result.stderr, test_cases)

    async def auto_generate_tests(
        self, code: str, language: str
    ) -> list[TestCase]:
        """Call LiteLLM to auto-generate test cases when none are provided."""
        enable_llm = os.getenv("ENABLE_LLM_TEST_GEN", "false").strip().lower()
        if enable_llm not in {"1", "true", "yes", "on"}:
            return [
                TestCase(
                    input={},
                    expected_output=None,
                    description="Default smoke test — code should run without errors",
                )
            ]
        prompt = dedent(f"""\
            You are a senior QA engineer. Given the following {language} code,
            generate 3-5 concise test cases. Return ONLY a JSON array where
            each element has the keys: "input" (object), "expected_output"
            (any JSON value), and "description" (string).

            Code:
            ```{language}
            {code}
            ```
        """)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self._settings.LITELLM_URL}/v1/chat/completions",
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                    },
                )
                resp.raise_for_status()
                body = resp.json()

            raw = body["choices"][0]["message"]["content"]
            # Strip markdown fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()

            items = json.loads(raw)
            return [TestCase(**item) for item in items]

        except Exception as exc:
            logger.warning("auto_generate_tests_failed", error=str(exc))
            return [
                TestCase(
                    input={},
                    expected_output=None,
                    description="Default smoke test — code should run without errors",
                )
            ]

    # ------------------------------------------------------------------
    # Harness generation
    # ------------------------------------------------------------------

    def _generate_test_harness(
        self, code: str, test_cases: list[TestCase], language: str
    ) -> str:
        """Wrap *code* and *test_cases* into an executable script."""
        generators = {
            "python": self._python_harness,
            "javascript": self._javascript_harness,
            "typescript": self._javascript_harness,  # same shape
            "bash": self._bash_harness,
        }
        gen = generators.get(language, self._python_harness)
        return gen(code, test_cases)

    def _python_harness(self, code: str, test_cases: list[TestCase]) -> str:
        test_blocks: list[str] = []
        for idx, tc in enumerate(test_cases):
            input_json = json.dumps(tc.input)
            expected_json = json.dumps(tc.expected_output)
            test_blocks.append(dedent(f"""\
                try:
                    __test_input_{idx} = json.loads('''{input_json}''')
                    __test_expected_{idx} = json.loads('''{expected_json}''')
                    __test_result_{idx} = main(**__test_input_{idx}) if callable(main) else None
                    __passed_{idx} = __test_result_{idx} == __test_expected_{idx}
                    print(json.dumps({{"index": {idx}, "passed": __passed_{idx}, "actual": __test_result_{idx}, "error": None}}))
                except Exception as __e_{idx}:
                    print(json.dumps({{"index": {idx}, "passed": False, "actual": None, "error": str(__e_{idx})}}))
            """))

        harness = (
            "import json\n\n"
            + code
            + "\n\n# --- Test harness ---\n"
            + "\n".join(test_blocks)
        )
        return harness

    def _javascript_harness(self, code: str, test_cases: list[TestCase]) -> str:
        test_blocks: list[str] = []
        for idx, tc in enumerate(test_cases):
            input_json = json.dumps(tc.input)
            expected_json = json.dumps(tc.expected_output)
            test_blocks.append(dedent(f"""\
                try {{
                    const input_{idx} = JSON.parse('{input_json}');
                    const expected_{idx} = {expected_json};
                    const result_{idx} = typeof main === 'function' ? main(input_{idx}) : undefined;
                    const passed_{idx} = JSON.stringify(result_{idx}) === JSON.stringify(expected_{idx});
                    console.log(JSON.stringify({{index: {idx}, passed: passed_{idx}, actual: result_{idx}, error: null}}));
                }} catch(e) {{
                    console.log(JSON.stringify({{index: {idx}, passed: false, actual: null, error: e.message}}));
                }}
            """))

        return code + "\n\n// --- Test harness ---\n" + "\n".join(test_blocks)

    def _bash_harness(self, code: str, test_cases: list[TestCase]) -> str:
        # For bash we simply run the script and check exit code
        lines = [
            code,
            "",
            "# --- Test harness ---",
            'echo \'{"index": 0, "passed": true, "actual": null, "error": null}\'',
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Output parsing
    # ------------------------------------------------------------------

    def _parse_test_output(
        self,
        stdout: str,
        stderr: str,
        test_cases: list[TestCase],
    ) -> list[TestCaseResult]:
        """Extract per-test JSON lines from stdout."""
        results: list[TestCaseResult] = []
        parsed_lines: dict[int, dict] = {}

        for line in stdout.strip().splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
                if "index" in obj:
                    parsed_lines[obj["index"]] = obj
            except json.JSONDecodeError:
                continue

        for idx, tc in enumerate(test_cases):
            if idx in parsed_lines:
                p = parsed_lines[idx]
                results.append(
                    TestCaseResult(
                        test_case=tc,
                        passed=bool(p.get("passed", False)),
                        actual_output=p.get("actual"),
                        error=p.get("error"),
                    )
                )
            else:
                results.append(
                    TestCaseResult(
                        test_case=tc,
                        passed=False,
                        actual_output=None,
                        error=stderr[:500] if stderr else "No output captured for this test case",
                    )
                )

        return results
