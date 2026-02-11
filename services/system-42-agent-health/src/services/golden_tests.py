"""
System 42 — Golden Test Suite.

Golden tests are canonical prompts whose correct outputs are well
understood.  The runner sends each prompt to an agent, then checks
that expected patterns are present and undesirable patterns are absent.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

from src.config import settings
from src.models import GoldenTestResult

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# ── Golden test definitions ─────────────────────────────────────────
# Each test case carries:
#   - prompt:           the user request
#   - patterns_present: regexes that MUST appear in the output
#   - patterns_absent:  regexes that MUST NOT appear in the output

GoldenTest = dict[str, Any]

GOLDEN_TESTS: list[GoldenTest] = [
    {
        "test_id": "crud-api",
        "prompt": (
            "Write a complete FastAPI CRUD API for a 'Task' resource with "
            "fields: id, title, description, completed.  Include all four "
            "HTTP methods and Pydantic models."
        ),
        "patterns_present": [
            r"(?i)class\s+Task",               # Pydantic/dataclass model
            r"(?i)@app\.(get|post|put|patch|delete)",  # route decorators
            r"(?i)async\s+def",                 # async handlers
            r"(?i)(BaseModel|pydantic)",        # Pydantic usage
        ],
        "patterns_absent": [
            r"(?i)TODO",                        # unfinished stubs
            r"(?i)pass\s*$",                    # empty function body
        ],
    },
    {
        "test_id": "auth-system",
        "prompt": (
            "Write a JWT authentication system in Python with login, "
            "token generation, and a protected endpoint."
        ),
        "patterns_present": [
            r"(?i)(jwt|jose|jsonwebtoken)",     # JWT library
            r"(?i)(encode|decode)",             # token ops
            r"(?i)(password|hash|bcrypt|passlib)",  # password handling
            r"(?i)Bearer",                      # auth header
        ],
        "patterns_absent": [
            r"(?i)password\s*=\s*['\"][^'\"]+['\"]",  # hardcoded password
        ],
    },
    {
        "test_id": "websocket-chat",
        "prompt": (
            "Write a WebSocket chat server using FastAPI that supports "
            "multiple connected clients with broadcast messaging."
        ),
        "patterns_present": [
            r"(?i)WebSocket",
            r"(?i)(broadcast|send_text|send_json)",
            r"(?i)(connect|disconnect|accept)",
            r"(?i)async\s+def",
        ],
        "patterns_absent": [
            r"(?i)TODO",
        ],
    },
    {
        "test_id": "background-worker",
        "prompt": (
            "Write a Python background worker that processes jobs from a "
            "Redis queue with retry logic and dead-letter handling."
        ),
        "patterns_present": [
            r"(?i)redis",
            r"(?i)(retry|attempt|backoff|max_retries)",
            r"(?i)(dead.letter|dlq|failed)",
            r"(?i)(while|loop|consume|listen)",
        ],
        "patterns_absent": [
            r"(?i)time\.sleep\(\d{3,}\)",       # unreasonably long sleep
        ],
    },
    {
        "test_id": "cli-tool",
        "prompt": (
            "Write a Python CLI tool using argparse or click that reads a "
            "CSV file, filters rows by a user-specified column value, and "
            "outputs the result as JSON."
        ),
        "patterns_present": [
            r"(?i)(argparse|click|typer)",
            r"(?i)(csv|DictReader|reader)",
            r"(?i)json",
            r"(?i)(filter|where|match)",
        ],
        "patterns_absent": [
            r"(?i)eval\(",                      # dangerous eval
        ],
    },
]


class GoldenTestRunner:
    """Sends golden prompts and scores the generated output."""

    def __init__(self) -> None:
        self._results_store: dict[str, list[GoldenTestResult]] = {}

    async def _send_prompt(self, agent_id: str, prompt: str) -> str:
        """Call the LiteLLM proxy and return the generated text."""
        payload = {
            "model": agent_id,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior software engineer.  "
                        "Respond ONLY with complete, production-ready code.  "
                        "No markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 4096,
        }
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{settings.LITELLM_URL}/v1/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.error(
                "golden_test_prompt_failed",
                agent_id=agent_id,
                error=str(exc),
            )
            return ""

    def _score(
        self,
        code: str,
        patterns_present: list[str],
        patterns_absent: list[str],
    ) -> tuple[bool, float, dict[str, Any]]:
        """Score the generated code against expected patterns.

        Returns (passed, score, details).
        """
        if not code:
            return False, 0.0, {"error": "empty response"}

        present_hits: list[str] = []
        present_misses: list[str] = []
        for pattern in patterns_present:
            if re.search(pattern, code, re.MULTILINE):
                present_hits.append(pattern)
            else:
                present_misses.append(pattern)

        absent_violations: list[str] = []
        for pattern in patterns_absent:
            if re.search(pattern, code, re.MULTILINE):
                absent_violations.append(pattern)

        total_checks = len(patterns_present) + len(patterns_absent)
        passed_checks = len(present_hits) + (
            len(patterns_absent) - len(absent_violations)
        )
        score = passed_checks / total_checks if total_checks else 0.0

        passed = len(present_misses) == 0 and len(absent_violations) == 0

        details: dict[str, Any] = {
            "patterns_matched": present_hits,
            "patterns_missing": present_misses,
            "unwanted_patterns_found": absent_violations,
            "checks_passed": passed_checks,
            "checks_total": total_checks,
        }
        return passed, round(score, 4), details

    async def run_suite(self, agent_id: str) -> list[GoldenTestResult]:
        """Run all golden tests against *agent_id*."""
        results: list[GoldenTestResult] = []

        for test in GOLDEN_TESTS:
            code = await self._send_prompt(agent_id, test["prompt"])
            passed, score, details = self._score(
                code,
                test["patterns_present"],
                test["patterns_absent"],
            )
            result = GoldenTestResult(
                test_id=test["test_id"],
                agent_id=agent_id,
                passed=passed,
                score=score,
                details=details,
            )
            results.append(result)
            logger.info(
                "golden_test_result",
                test_id=test["test_id"],
                agent_id=agent_id,
                passed=passed,
                score=score,
            )

        self._results_store.setdefault(agent_id, []).extend(results)

        passed_count = sum(1 for r in results if r.passed)
        logger.info(
            "golden_test_suite_complete",
            agent_id=agent_id,
            total=len(results),
            passed=passed_count,
            failed=len(results) - passed_count,
        )
        return results

    def get_results(self, agent_id: str | None = None) -> list[GoldenTestResult]:
        """Return stored results, optionally filtered by agent."""
        if agent_id:
            return list(self._results_store.get(agent_id, []))
        return [r for rs in self._results_store.values() for r in rs]
