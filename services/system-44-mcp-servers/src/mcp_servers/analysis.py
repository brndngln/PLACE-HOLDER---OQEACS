"""
System 44 — MCP Analysis Server (port 8335).

Provides AI-powered code analysis tools accessible to coding agents via
the Model Context Protocol.  Tools include static analysis, antipattern
detection, cyclomatic complexity measurement, and OWASP security checks.
"""

from __future__ import annotations

import ast
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
    AnalysisRequest,
    AnalysisResult,
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

logger: structlog.stdlib.BoundLogger = structlog.get_logger("system44.analysis")

# ── Prometheus metrics ──────────────────────────────────────────────

REGISTRY = CollectorRegistry()
REQUEST_COUNT = Counter(
    "mcp_analysis_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)
TOOL_CALLS = Counter(
    "mcp_analysis_tool_calls_total",
    "Total tool invocations",
    ["tool_name", "status"],
    registry=REGISTRY,
)
UPTIME_GAUGE = Gauge(
    "mcp_analysis_uptime_seconds",
    "Seconds since service started",
    registry=REGISTRY,
)

_start_time: datetime | None = None
_http_client: httpx.AsyncClient | None = None

# ── Tool definitions ────────────────────────────────────────────────

ANALYSIS_TOOLS: list[MCPToolDefinition] = [
    MCPToolDefinition(
        name="analyze_code",
        description=(
            "Perform a comprehensive code review using LLM.  Returns issues "
            "categorised by severity (critical, high, medium, low, info) with "
            "line numbers and suggested fixes."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code to review"},
                "language": {"type": "string", "default": "python"},
                "analysis_type": {
                    "type": "string",
                    "enum": ["full", "security", "performance", "style"],
                    "default": "full",
                },
            },
            "required": ["code"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "issues": {"type": "array"},
                "metrics": {"type": "object"},
                "suggestions": {"type": "array"},
            },
        },
    ),
    MCPToolDefinition(
        name="detect_antipatterns",
        description=(
            "Query the Qdrant engineering_antipatterns collection for known "
            "antipatterns present in the submitted code.  Returns matched "
            "patterns with remediation guidance."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code to scan"},
                "language": {"type": "string", "default": "python"},
            },
            "required": ["code"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "antipatterns": {"type": "array"},
                "total_found": {"type": "integer"},
            },
        },
    ),
    MCPToolDefinition(
        name="measure_complexity",
        description=(
            "Calculate cyclomatic complexity and related metrics for the "
            "provided source code.  Supports Python with AST-based analysis."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code to measure"},
                "language": {"type": "string", "default": "python"},
            },
            "required": ["code"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "cyclomatic_complexity": {"type": "integer"},
                "functions": {"type": "array"},
                "loc": {"type": "integer"},
                "sloc": {"type": "integer"},
            },
        },
    ),
    MCPToolDefinition(
        name="check_security",
        description=(
            "Run OWASP-informed security checks on the submitted code using "
            "LLM analysis.  Identifies injection vulnerabilities, hardcoded "
            "secrets, insecure defaults, and more."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code to audit"},
                "language": {"type": "string", "default": "python"},
            },
            "required": ["code"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "vulnerabilities": {"type": "array"},
                "risk_score": {"type": "number"},
                "recommendations": {"type": "array"},
            },
        },
    ),
]

_TOOL_MAP: dict[str, MCPToolDefinition] = {t.name: t for t in ANALYSIS_TOOLS}


# ── Tool implementations ────────────────────────────────────────────


async def _llm_chat(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Send a chat completion request to LiteLLM and return the text."""
    assert _http_client is not None
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    try:
        resp = await _http_client.post(
            f"{settings.LITELLM_URL}/v1/chat/completions",
            json=payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.error("litellm_request_failed", error=str(exc))
        raise


async def _tool_analyze_code(arguments: dict[str, Any]) -> dict[str, Any]:
    """Comprehensive LLM-based code review."""
    code = arguments.get("code", "")
    language = arguments.get("language", "python")
    analysis_type = arguments.get("analysis_type", "full")

    system_prompt = (
        "You are an expert code reviewer.  Analyse the provided code and return "
        "a JSON object with three keys:\n"
        '- "issues": array of objects with keys "severity" (critical|high|medium|low|info), '
        '"line" (integer or null), "message" (string), "rule" (string identifier)\n'
        '- "metrics": object with "loc" (lines of code), "functions" (count), '
        '"classes" (count), "complexity_estimate" (string)\n'
        '- "suggestions": array of actionable improvement strings\n'
        f"Focus on: {analysis_type} analysis.  Language: {language}.\n"
        "Return ONLY valid JSON, no markdown fencing."
    )

    try:
        raw = await _llm_chat(system_prompt, code)
        # Attempt to parse the LLM response as JSON
        import json

        # Strip potential markdown fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        result = json.loads(cleaned)
        return {
            "issues": result.get("issues", []),
            "metrics": result.get("metrics", {}),
            "suggestions": result.get("suggestions", []),
        }
    except Exception as exc:
        logger.warning("analyze_code_parse_error", error=str(exc))
        return {
            "issues": [],
            "metrics": {"raw_response": str(exc)},
            "suggestions": ["LLM analysis could not be parsed; review manually."],
        }


async def _tool_detect_antipatterns(arguments: dict[str, Any]) -> dict[str, Any]:
    """Query Qdrant engineering_antipatterns collection for matching antipatterns."""
    code = arguments.get("code", "")
    language = arguments.get("language", "python")

    assert _http_client is not None

    # Generate an embedding via LiteLLM for the code snippet
    try:
        embed_resp = await _http_client.post(
            f"{settings.LITELLM_URL}/v1/embeddings",
            json={
                "model": "text-embedding-3-small",
                "input": f"[{language}] {code[:2000]}",
            },
            timeout=30.0,
        )
        embed_resp.raise_for_status()
        vector = embed_resp.json()["data"][0]["embedding"]
    except Exception as exc:
        logger.warning("embedding_generation_failed", error=str(exc))
        return {"antipatterns": [], "total_found": 0, "error": str(exc)}

    # Search Qdrant
    try:
        search_resp = await _http_client.post(
            f"{settings.QDRANT_URL}/collections/engineering_antipatterns/points/search",
            json={
                "vector": vector,
                "limit": 10,
                "with_payload": True,
                "score_threshold": 0.6,
            },
            timeout=15.0,
        )
        search_resp.raise_for_status()
        hits = search_resp.json().get("result", [])
    except Exception as exc:
        logger.warning("qdrant_search_failed", error=str(exc))
        return {"antipatterns": [], "total_found": 0, "error": str(exc)}

    antipatterns = []
    for hit in hits:
        payload = hit.get("payload", {})
        antipatterns.append(
            {
                "name": payload.get("name", "unknown"),
                "description": payload.get("description", ""),
                "severity": payload.get("severity", "medium"),
                "remediation": payload.get("remediation", ""),
                "score": hit.get("score", 0.0),
            }
        )

    return {"antipatterns": antipatterns, "total_found": len(antipatterns)}


def _count_cyclomatic_complexity(node: ast.AST) -> int:
    """Recursively count decision points for cyclomatic complexity."""
    complexity = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, ast.Assert):
            complexity += 1
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            complexity += 1
    return complexity


async def _tool_measure_complexity(arguments: dict[str, Any]) -> dict[str, Any]:
    """Calculate cyclomatic complexity using Python AST analysis."""
    code = arguments.get("code", "")
    language = arguments.get("language", "python")

    if language != "python":
        return {
            "cyclomatic_complexity": -1,
            "functions": [],
            "loc": len(code.splitlines()),
            "sloc": len([ln for ln in code.splitlines() if ln.strip()]),
            "note": f"AST analysis only supports Python; received '{language}'.",
        }

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {
            "cyclomatic_complexity": -1,
            "functions": [],
            "loc": len(code.splitlines()),
            "sloc": 0,
            "error": f"Syntax error: {exc}",
        }

    lines = code.splitlines()
    loc = len(lines)
    sloc = len([ln for ln in lines if ln.strip() and not ln.strip().startswith("#")])

    functions_info: list[dict[str, Any]] = []
    total_complexity = 1  # Base complexity

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_complexity = 1 + _count_cyclomatic_complexity(node)
            functions_info.append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "complexity": func_complexity,
                    "args": len(node.args.args),
                }
            )
            total_complexity += func_complexity - 1
        elif isinstance(node, ast.ClassDef):
            pass  # Classes contribute through their methods

    total_complexity += _count_cyclomatic_complexity(tree)

    return {
        "cyclomatic_complexity": total_complexity,
        "functions": functions_info,
        "loc": loc,
        "sloc": sloc,
    }


async def _tool_check_security(arguments: dict[str, Any]) -> dict[str, Any]:
    """OWASP-informed security audit via LLM analysis."""
    code = arguments.get("code", "")
    language = arguments.get("language", "python")

    system_prompt = (
        "You are a senior application-security engineer.  Audit the provided code "
        "against the OWASP Top 10 and common vulnerability categories.\n\n"
        "Return a JSON object with:\n"
        '- "vulnerabilities": array of objects with keys "id" (e.g. "CWE-79"), '
        '"category" (e.g. "Injection"), "severity" (critical|high|medium|low), '
        '"description" (string), "line" (integer or null), "owasp_ref" (string)\n'
        '- "risk_score": float 0.0-10.0 (0 = no risk, 10 = critical)\n'
        '- "recommendations": array of actionable remediation strings\n'
        f"Language: {language}.  Return ONLY valid JSON, no markdown fencing."
    )

    try:
        raw = await _llm_chat(system_prompt, code)
        import json

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        result = json.loads(cleaned)
        return {
            "vulnerabilities": result.get("vulnerabilities", []),
            "risk_score": result.get("risk_score", 0.0),
            "recommendations": result.get("recommendations", []),
        }
    except Exception as exc:
        logger.warning("check_security_parse_error", error=str(exc))
        return {
            "vulnerabilities": [],
            "risk_score": -1.0,
            "recommendations": [f"Security analysis failed: {exc}"],
        }


# Dispatcher
_TOOL_DISPATCH: dict[str, Any] = {
    "analyze_code": _tool_analyze_code,
    "detect_antipatterns": _tool_detect_antipatterns,
    "measure_complexity": _tool_measure_complexity,
    "check_security": _tool_check_security,
}


# ── Lifespan ────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: set up and tear down shared resources."""
    global _start_time, _http_client  # noqa: PLW0603
    _start_time = datetime.now(timezone.utc)
    _http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

    logger.info(
        "mcp_analysis_started",
        service="mcp-analysis",
        port=8335,
    )

    yield

    await _http_client.aclose()
    _http_client = None
    logger.info("mcp_analysis_stopped")


# ── Application ─────────────────────────────────────────────────────

app = FastAPI(
    title="System 44 — MCP Analysis Server",
    description=(
        "Code analysis tools for AI coding agents.  Provides LLM-powered "
        "code review, antipattern detection, cyclomatic complexity measurement, "
        "and OWASP security checks."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["infra"])
async def health_check() -> dict[str, Any]:
    """Liveness / readiness probe."""
    return {
        "status": "healthy",
        "service": "mcp-analysis",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tools_available": len(ANALYSIS_TOOLS),
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
    """Return the list of available analysis tools."""
    REQUEST_COUNT.labels(method="GET", endpoint="/api/v1/tools", status="200").inc()
    return ANALYSIS_TOOLS


@app.post("/api/v1/tools/call", tags=["mcp"])
async def call_tool(request: MCPToolCall) -> MCPToolResult:
    """Execute an analysis tool by name."""
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
        await notify_tool_error("analysis", request.tool_name, error_msg)
        return MCPToolResult(
            tool_name=request.tool_name,
            error=error_msg,
            execution_time_ms=round(elapsed_ms, 2),
        )


# ── Dev entry-point ─────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "src.mcp_servers.analysis:app",
        host="0.0.0.0",
        port=8335,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
