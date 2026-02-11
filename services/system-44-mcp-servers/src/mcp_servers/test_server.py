"""
System 44 — MCP Test Server (port 8336).

Provides AI-powered test generation and analysis tools accessible to
coding agents via the Model Context Protocol.  Tools include test
generation, edge-case identification, coverage analysis, and fixture
creation.
"""

from __future__ import annotations

import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx
import structlog
import uvicorn
from fastapi import FastAPI, Response
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    generate_latest,
)

from src.config import settings
from src.models import (
    MCPToolCall,
    MCPToolDefinition,
    MCPToolResult,
)
from src.utils.notifications import notify_tool_error

# ── Structured logging ──────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.get_level_from_name(settings.LOG_LEVEL),
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger("system44.test")

# ── Prometheus metrics ──────────────────────────────────────────────

REGISTRY = CollectorRegistry()
REQUEST_COUNT = Counter(
    "mcp_test_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)
TOOL_CALLS = Counter(
    "mcp_test_tool_calls_total",
    "Total tool invocations",
    ["tool_name", "status"],
    registry=REGISTRY,
)
UPTIME_GAUGE = Gauge(
    "mcp_test_uptime_seconds",
    "Seconds since service started",
    registry=REGISTRY,
)

_start_time: datetime | None = None
_http_client: httpx.AsyncClient | None = None

# ── Tool definitions ────────────────────────────────────────────────

TEST_TOOLS: list[MCPToolDefinition] = [
    MCPToolDefinition(
        name="generate_tests",
        description=(
            "Generate a complete test suite for the provided source code using "
            "LLM analysis.  Produces ready-to-run tests targeting the specified "
            "test framework."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code to test"},
                "language": {"type": "string", "default": "python"},
                "framework": {
                    "type": "string",
                    "default": "pytest",
                    "description": "Target test framework (pytest, jest, go-test, etc.)",
                },
            },
            "required": ["code"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "tests": {"type": "string"},
                "coverage_estimate": {"type": "number"},
            },
        },
    ),
    MCPToolDefinition(
        name="suggest_test_cases",
        description=(
            "Analyse source code and identify edge cases, boundary conditions, "
            "and error scenarios that should be tested.  Returns structured "
            "test-case suggestions without generating code."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code to analyse"},
                "language": {"type": "string", "default": "python"},
            },
            "required": ["code"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "test_cases": {"type": "array"},
                "edge_cases": {"type": "array"},
                "error_scenarios": {"type": "array"},
            },
        },
    ),
    MCPToolDefinition(
        name="analyze_coverage",
        description=(
            "Parse a coverage report (JSON, LCOV, or Cobertura XML format) and "
            "return a summary with uncovered lines, branches, and suggestions "
            "for improving coverage."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "report": {"type": "string", "description": "Coverage report content"},
                "format": {
                    "type": "string",
                    "enum": ["json", "lcov", "cobertura"],
                    "default": "json",
                },
            },
            "required": ["report"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "total_coverage": {"type": "number"},
                "uncovered_lines": {"type": "array"},
                "branch_coverage": {"type": "number"},
                "suggestions": {"type": "array"},
            },
        },
    ),
    MCPToolDefinition(
        name="generate_fixtures",
        description=(
            "Create test fixtures and mock data for the provided code.  Analyses "
            "data models, function signatures, and external dependencies to "
            "produce realistic test fixtures."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code needing fixtures"},
                "language": {"type": "string", "default": "python"},
                "framework": {"type": "string", "default": "pytest"},
            },
            "required": ["code"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "fixtures": {"type": "string"},
                "mock_data": {"type": "object"},
            },
        },
    ),
]

_TOOL_MAP: dict[str, MCPToolDefinition] = {t.name: t for t in TEST_TOOLS}


# ── Tool implementations ────────────────────────────────────────────


async def _llm_chat(system_prompt: str, user_prompt: str) -> str:
    """Send a chat completion request to LiteLLM and return the text."""
    assert _http_client is not None
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
    }
    try:
        resp = await _http_client.post(
            f"{settings.LITELLM_URL}/v1/chat/completions",
            json=payload,
            timeout=90.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.error("litellm_request_failed", error=str(exc))
        raise


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned


async def _tool_generate_tests(arguments: dict[str, Any]) -> dict[str, Any]:
    """Generate a complete test suite using LLM analysis."""
    code = arguments.get("code", "")
    language = arguments.get("language", "python")
    framework = arguments.get("framework", "pytest")

    system_prompt = (
        f"You are an expert test engineer.  Generate a complete, runnable test suite "
        f"for the provided {language} code using the {framework} framework.\n\n"
        "Requirements:\n"
        "- Test all public functions and methods\n"
        "- Include happy path, edge cases, and error scenarios\n"
        "- Use descriptive test names\n"
        "- Add docstrings explaining each test's purpose\n"
        "- Include necessary imports\n"
        "- Use mocks for external dependencies\n\n"
        "After the test code, on a new line write:\n"
        "COVERAGE_ESTIMATE: <number>\n"
        "where <number> is your estimate of code coverage percentage (0-100)."
    )

    try:
        raw = await _llm_chat(system_prompt, code)

        # Extract coverage estimate
        coverage_estimate = 0.0
        coverage_match = re.search(r"COVERAGE_ESTIMATE:\s*([\d.]+)", raw)
        if coverage_match:
            coverage_estimate = min(float(coverage_match.group(1)), 100.0)

        # Extract test code (everything before COVERAGE_ESTIMATE)
        test_code = re.split(r"\nCOVERAGE_ESTIMATE:", raw)[0]
        test_code = _strip_markdown_fences(test_code).strip()

        return {
            "tests": test_code,
            "coverage_estimate": coverage_estimate,
        }
    except Exception as exc:
        logger.warning("generate_tests_failed", error=str(exc))
        return {
            "tests": f"# Test generation failed: {exc}",
            "coverage_estimate": 0.0,
        }


async def _tool_suggest_test_cases(arguments: dict[str, Any]) -> dict[str, Any]:
    """Identify edge cases and boundary conditions for testing."""
    code = arguments.get("code", "")
    language = arguments.get("language", "python")

    system_prompt = (
        "You are an expert QA engineer.  Analyse the provided code and identify "
        "all test cases that should be written.  Return a JSON object with:\n"
        '- "test_cases": array of objects with "name" (string), "description" (string), '
        '"type" (unit|integration|e2e), "priority" (high|medium|low)\n'
        '- "edge_cases": array of objects with "scenario" (string), '
        '"input_description" (string), "expected_behavior" (string)\n'
        '- "error_scenarios": array of objects with "trigger" (string), '
        '"expected_error" (string), "severity" (string)\n'
        f"Language: {language}.  Return ONLY valid JSON, no markdown fencing."
    )

    try:
        import json

        raw = await _llm_chat(system_prompt, code)
        cleaned = _strip_markdown_fences(raw)
        result = json.loads(cleaned)
        return {
            "test_cases": result.get("test_cases", []),
            "edge_cases": result.get("edge_cases", []),
            "error_scenarios": result.get("error_scenarios", []),
        }
    except Exception as exc:
        logger.warning("suggest_test_cases_failed", error=str(exc))
        return {
            "test_cases": [],
            "edge_cases": [],
            "error_scenarios": [],
            "error": str(exc),
        }


async def _tool_analyze_coverage(arguments: dict[str, Any]) -> dict[str, Any]:
    """Parse a coverage report and return a summary."""
    import json

    report_text = arguments.get("report", "")
    report_format = arguments.get("format", "json")

    if report_format == "json":
        try:
            report = json.loads(report_text)

            # Handle coverage.py JSON format
            totals = report.get("totals", {})
            total_coverage = totals.get("percent_covered", 0.0)
            branch_coverage = totals.get("percent_covered_branches", 0.0)

            uncovered_lines: list[dict[str, Any]] = []
            files_data = report.get("files", {})
            for filepath, file_info in files_data.items():
                missing = file_info.get("missing_lines", [])
                if missing:
                    uncovered_lines.append(
                        {
                            "file": filepath,
                            "lines": missing,
                            "count": len(missing),
                        }
                    )

            suggestions = []
            if total_coverage < 80:
                suggestions.append(
                    f"Overall coverage is {total_coverage:.1f}% — aim for at least 80%."
                )
            for item in sorted(uncovered_lines, key=lambda x: x["count"], reverse=True)[:5]:
                suggestions.append(
                    f"Add tests for {item['file']} — {item['count']} uncovered lines."
                )

            return {
                "total_coverage": total_coverage,
                "uncovered_lines": uncovered_lines,
                "branch_coverage": branch_coverage,
                "suggestions": suggestions,
            }
        except json.JSONDecodeError as exc:
            return {
                "total_coverage": 0.0,
                "uncovered_lines": [],
                "branch_coverage": 0.0,
                "suggestions": [f"Failed to parse JSON coverage report: {exc}"],
            }

    elif report_format == "lcov":
        # Parse LCOV format
        total_lines = 0
        covered_lines = 0
        total_branches = 0
        covered_branches = 0
        uncovered_files: list[dict[str, Any]] = []
        current_file = ""
        current_missing: list[int] = []

        for line in report_text.splitlines():
            if line.startswith("SF:"):
                current_file = line[3:]
                current_missing = []
            elif line.startswith("DA:"):
                parts = line[3:].split(",")
                line_no = int(parts[0])
                hits = int(parts[1])
                total_lines += 1
                if hits > 0:
                    covered_lines += 1
                else:
                    current_missing.append(line_no)
            elif line.startswith("BRDA:"):
                total_branches += 1
                parts = line[5:].split(",")
                if len(parts) >= 4 and parts[3] != "-" and int(parts[3]) > 0:
                    covered_branches += 1
            elif line.startswith("end_of_record"):
                if current_missing:
                    uncovered_files.append(
                        {"file": current_file, "lines": current_missing, "count": len(current_missing)}
                    )

        total_cov = (covered_lines / total_lines * 100) if total_lines > 0 else 0.0
        branch_cov = (covered_branches / total_branches * 100) if total_branches > 0 else 0.0

        suggestions = []
        if total_cov < 80:
            suggestions.append(f"Overall coverage is {total_cov:.1f}% — aim for at least 80%.")
        for item in sorted(uncovered_files, key=lambda x: x["count"], reverse=True)[:5]:
            suggestions.append(f"Add tests for {item['file']} — {item['count']} uncovered lines.")

        return {
            "total_coverage": round(total_cov, 2),
            "uncovered_lines": uncovered_files,
            "branch_coverage": round(branch_cov, 2),
            "suggestions": suggestions,
        }

    else:
        # For cobertura XML or unknown formats, use LLM to parse
        system_prompt = (
            "Parse the following coverage report and return a JSON object with:\n"
            '- "total_coverage": float (percentage 0-100)\n'
            '- "uncovered_lines": array of {"file": string, "lines": array of int}\n'
            '- "branch_coverage": float (percentage 0-100)\n'
            '- "suggestions": array of strings\n'
            "Return ONLY valid JSON, no markdown fencing."
        )
        try:
            raw = await _llm_chat(system_prompt, report_text)
            cleaned = _strip_markdown_fences(raw)
            result = json.loads(cleaned)
            return {
                "total_coverage": result.get("total_coverage", 0.0),
                "uncovered_lines": result.get("uncovered_lines", []),
                "branch_coverage": result.get("branch_coverage", 0.0),
                "suggestions": result.get("suggestions", []),
            }
        except Exception as exc:
            return {
                "total_coverage": 0.0,
                "uncovered_lines": [],
                "branch_coverage": 0.0,
                "suggestions": [f"Failed to parse {report_format} report: {exc}"],
            }


async def _tool_generate_fixtures(arguments: dict[str, Any]) -> dict[str, Any]:
    """Create test fixtures and mock data for the provided code."""
    code = arguments.get("code", "")
    language = arguments.get("language", "python")
    framework = arguments.get("framework", "pytest")

    system_prompt = (
        f"You are an expert test engineer.  Analyse the provided {language} code and "
        f"generate test fixtures and mock data for the {framework} framework.\n\n"
        "Return a JSON object with:\n"
        '- "fixtures": string containing the fixture/setup code (ready to run)\n'
        '- "mock_data": object with representative test data for each data model, '
        "function parameter, or external dependency found in the code\n\n"
        "Return ONLY valid JSON, no markdown fencing."
    )

    try:
        import json

        raw = await _llm_chat(system_prompt, code)
        cleaned = _strip_markdown_fences(raw)
        result = json.loads(cleaned)
        return {
            "fixtures": result.get("fixtures", ""),
            "mock_data": result.get("mock_data", {}),
        }
    except Exception as exc:
        logger.warning("generate_fixtures_failed", error=str(exc))
        return {
            "fixtures": f"# Fixture generation failed: {exc}",
            "mock_data": {},
        }


# Dispatcher
_TOOL_DISPATCH: dict[str, Any] = {
    "generate_tests": _tool_generate_tests,
    "suggest_test_cases": _tool_suggest_test_cases,
    "analyze_coverage": _tool_analyze_coverage,
    "generate_fixtures": _tool_generate_fixtures,
}


# ── Lifespan ────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: set up and tear down shared resources."""
    global _start_time, _http_client  # noqa: PLW0603
    _start_time = datetime.now(timezone.utc)
    _http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

    logger.info(
        "mcp_test_started",
        service="mcp-test",
        port=8336,
    )

    yield

    await _http_client.aclose()
    _http_client = None
    logger.info("mcp_test_stopped")


# ── Application ─────────────────────────────────────────────────────

app = FastAPI(
    title="System 44 — MCP Test Server",
    description=(
        "Test generation and analysis tools for AI coding agents.  Provides "
        "LLM-powered test generation, edge-case identification, coverage "
        "analysis, and fixture creation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["infra"])
async def health_check() -> dict[str, Any]:
    """Liveness / readiness probe."""
    return {
        "status": "healthy",
        "service": "mcp-test",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tools_available": len(TEST_TOOLS),
    }


@app.get("/metrics", tags=["infra"])
async def prometheus_metrics() -> Response:
    """Prometheus-compatible metrics scrape endpoint."""
    if _start_time is not None:
        elapsed = (datetime.now(timezone.utc) - _start_time).total_seconds()
        UPTIME_GAUGE.set(elapsed)
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/api/v1/tools", tags=["mcp"])
async def list_tools() -> list[MCPToolDefinition]:
    """Return the list of available test tools."""
    REQUEST_COUNT.labels(method="GET", endpoint="/api/v1/tools", status="200").inc()
    return TEST_TOOLS


@app.post("/api/v1/tools/call", tags=["mcp"])
async def call_tool(request: MCPToolCall) -> MCPToolResult:
    """Execute a test tool by name."""
    start = time.perf_counter()

    if request.tool_name not in _TOOL_DISPATCH:
        TOOL_CALLS.labels(tool_name=request.tool_name, status="not_found").inc()
        return MCPToolResult(
            tool_name=request.tool_name,
            error=f"Unknown tool: {request.tool_name}. Available: {list(_TOOL_DISPATCH.keys())}",
            execution_time_ms=0.0,
        )

    handler = _TOOL_DISPATCH[request.tool_name]

    try:
        result = await handler(request.arguments)
        elapsed_ms = (time.perf_counter() - start) * 1000
        TOOL_CALLS.labels(tool_name=request.tool_name, status="success").inc()
        logger.info(
            "tool_call_success",
            tool=request.tool_name,
            elapsed_ms=round(elapsed_ms, 2),
        )
        return MCPToolResult(
            tool_name=request.tool_name,
            result=result,
            execution_time_ms=round(elapsed_ms, 2),
        )
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        TOOL_CALLS.labels(tool_name=request.tool_name, status="error").inc()
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error("tool_call_failed", tool=request.tool_name, error=error_msg)
        await notify_tool_error("test", request.tool_name, error_msg)
        return MCPToolResult(
            tool_name=request.tool_name,
            error=error_msg,
            execution_time_ms=round(elapsed_ms, 2),
        )


# ── Dev entry-point ─────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "src.mcp_servers.test_server:app",
        host="0.0.0.0",
        port=8336,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
