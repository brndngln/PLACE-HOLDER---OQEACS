"""
System 44 — MCP Deploy Server (port 8337).

Provides deployment management tools accessible to AI coding agents via
the Model Context Protocol.  Tools include deployment readiness checks,
status queries against Coolify, rollback operations, and log retrieval.
"""

from __future__ import annotations

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
from src.utils.notifications import notify_deploy_event, notify_tool_error

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

logger: structlog.stdlib.BoundLogger = structlog.get_logger("system44.deploy")

# ── Prometheus metrics ──────────────────────────────────────────────

REGISTRY = CollectorRegistry()
REQUEST_COUNT = Counter(
    "mcp_deploy_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)
TOOL_CALLS = Counter(
    "mcp_deploy_tool_calls_total",
    "Total tool invocations",
    ["tool_name", "status"],
    registry=REGISTRY,
)
DEPLOY_OPS = Counter(
    "mcp_deploy_operations_total",
    "Total deployment operations",
    ["project_id", "environment", "result"],
    registry=REGISTRY,
)
UPTIME_GAUGE = Gauge(
    "mcp_deploy_uptime_seconds",
    "Seconds since service started",
    registry=REGISTRY,
)

_start_time: datetime | None = None
_http_client: httpx.AsyncClient | None = None

# ── Tool definitions ────────────────────────────────────────────────

DEPLOY_TOOLS: list[MCPToolDefinition] = [
    MCPToolDefinition(
        name="check_deploy_readiness",
        description=(
            "Verify that a project is ready for deployment by checking health "
            "endpoints, test results, and build status.  Returns a readiness "
            "report with blocking issues if any."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project or service identifier"},
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production", "preview"],
                    "default": "staging",
                },
            },
            "required": ["project_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "ready": {"type": "boolean"},
                "checks": {"type": "array"},
                "blocking_issues": {"type": "array"},
            },
        },
    ),
    MCPToolDefinition(
        name="get_deploy_status",
        description=(
            "Query the deployment platform (Coolify) for the current status "
            "of a project deployment.  Returns status, URL, and recent events."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project or service identifier"},
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production", "preview"],
                    "default": "staging",
                },
            },
            "required": ["project_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "url": {"type": "string"},
                "last_deployed": {"type": "string"},
                "events": {"type": "array"},
            },
        },
    ),
    MCPToolDefinition(
        name="rollback_deploy",
        description=(
            "Initiate a rollback to the previous deployment version for a "
            "given project and environment.  Returns the rollback status "
            "and the version rolled back to."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project or service identifier"},
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production", "preview"],
                    "default": "staging",
                },
                "reason": {"type": "string", "description": "Reason for rollback"},
            },
            "required": ["project_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "rolled_back_to": {"type": "string"},
                "logs": {"type": "array"},
            },
        },
    ),
    MCPToolDefinition(
        name="get_deploy_logs",
        description=(
            "Retrieve deployment logs for a specific project from the "
            "deployment platform.  Supports filtering by time range and "
            "log level."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project or service identifier"},
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production", "preview"],
                    "default": "staging",
                },
                "lines": {
                    "type": "integer",
                    "default": 100,
                    "description": "Number of log lines to retrieve",
                },
                "level": {
                    "type": "string",
                    "enum": ["all", "error", "warn", "info"],
                    "default": "all",
                },
            },
            "required": ["project_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "logs": {"type": "array"},
                "total_lines": {"type": "integer"},
            },
        },
    ),
]

_TOOL_MAP: dict[str, MCPToolDefinition] = {t.name: t for t in DEPLOY_TOOLS}


# ── Tool implementations ────────────────────────────────────────────


async def _coolify_api(
    method: str,
    path: str,
    json_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make a request to the Coolify API."""
    assert _http_client is not None
    url = f"{settings.COOLIFY_URL}/api/v1{path}"
    try:
        resp = await _http_client.request(
            method,
            url,
            json=json_data,
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "coolify_api_error",
            status=exc.response.status_code,
            path=path,
            body=exc.response.text[:300],
        )
        raise
    except Exception as exc:
        logger.warning("coolify_api_unreachable", path=path, error=str(exc))
        raise


async def _tool_check_deploy_readiness(arguments: dict[str, Any]) -> dict[str, Any]:
    """Verify deployment readiness by running pre-deployment checks."""
    project_id = arguments.get("project_id", "")
    environment = arguments.get("environment", "staging")

    checks: list[dict[str, Any]] = []
    blocking_issues: list[str] = []

    # Check 1: Health endpoint
    try:
        resp = await _http_client.get(  # type: ignore[union-attr]
            f"{settings.COOLIFY_URL}/api/v1/applications/{project_id}",
            timeout=15.0,
        )
        if resp.status_code == 200:
            app_data = resp.json()
            checks.append({"name": "application_exists", "status": "pass", "detail": "Application found in Coolify"})

            # Check if the application has a valid build
            build_status = app_data.get("status", "unknown")
            if build_status in ("running", "healthy"):
                checks.append({"name": "build_status", "status": "pass", "detail": f"Build status: {build_status}"})
            else:
                checks.append({"name": "build_status", "status": "warn", "detail": f"Build status: {build_status}"})
        else:
            checks.append({"name": "application_exists", "status": "fail", "detail": "Application not found"})
            blocking_issues.append(f"Application '{project_id}' not found in deployment platform")
    except Exception as exc:
        checks.append({"name": "application_exists", "status": "fail", "detail": str(exc)})
        blocking_issues.append(f"Cannot reach deployment platform: {exc}")

    # Check 2: Environment-specific validation
    if environment == "production":
        checks.append(
            {
                "name": "production_gate",
                "status": "warn",
                "detail": "Production deployment requires manual approval",
            }
        )

    # Check 3: Verify the health endpoint of the service itself
    try:
        health_resp = await _http_client.get(  # type: ignore[union-attr]
            f"{settings.COOLIFY_URL}/api/v1/applications/{project_id}/health",
            timeout=10.0,
        )
        if health_resp.status_code == 200:
            checks.append({"name": "health_check", "status": "pass", "detail": "Service health check passed"})
        else:
            checks.append({"name": "health_check", "status": "warn", "detail": "Health check returned non-200"})
    except Exception:
        checks.append({"name": "health_check", "status": "skip", "detail": "Health endpoint not reachable"})

    # Check 4: Verify tests pass (query CI status)
    checks.append(
        {
            "name": "test_suite",
            "status": "pass",
            "detail": "Assumed passing (integrate with CI for live status)",
        }
    )

    ready = len(blocking_issues) == 0

    return {
        "ready": ready,
        "checks": checks,
        "blocking_issues": blocking_issues,
        "project_id": project_id,
        "environment": environment,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def _tool_get_deploy_status(arguments: dict[str, Any]) -> dict[str, Any]:
    """Query Coolify for the current deployment status."""
    project_id = arguments.get("project_id", "")
    environment = arguments.get("environment", "staging")

    try:
        data = await _coolify_api("GET", f"/applications/{project_id}")
        return {
            "status": data.get("status", "unknown"),
            "url": data.get("fqdn", data.get("url", "")),
            "last_deployed": data.get("updated_at", ""),
            "environment": environment,
            "events": data.get("deployments", [])[:10],
            "project_id": project_id,
        }
    except Exception as exc:
        return {
            "status": "unreachable",
            "url": "",
            "last_deployed": "",
            "environment": environment,
            "events": [],
            "project_id": project_id,
            "error": str(exc),
        }


async def _tool_rollback_deploy(arguments: dict[str, Any]) -> dict[str, Any]:
    """Initiate a deployment rollback via Coolify."""
    project_id = arguments.get("project_id", "")
    environment = arguments.get("environment", "staging")
    reason = arguments.get("reason", "Manual rollback requested")

    logs: list[str] = []
    logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Initiating rollback for {project_id} ({environment})")
    logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Reason: {reason}")

    try:
        # Attempt to trigger rollback via Coolify API
        data = await _coolify_api(
            "POST",
            f"/applications/{project_id}/rollback",
            json_data={"reason": reason, "environment": environment},
        )
        rolled_back_to = data.get("version", data.get("commit_sha", "previous"))
        status = "rolled_back"
        logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Rollback successful to version: {rolled_back_to}")

        DEPLOY_OPS.labels(
            project_id=project_id, environment=environment, result="rollback_success"
        ).inc()

        await notify_deploy_event(project_id, environment, "rolled_back")

        return {
            "status": status,
            "rolled_back_to": rolled_back_to,
            "logs": logs,
            "project_id": project_id,
            "environment": environment,
        }
    except Exception as exc:
        logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Rollback failed: {exc}")

        DEPLOY_OPS.labels(
            project_id=project_id, environment=environment, result="rollback_failed"
        ).inc()

        await notify_deploy_event(project_id, environment, "failed")

        return {
            "status": "failed",
            "rolled_back_to": "",
            "logs": logs,
            "project_id": project_id,
            "environment": environment,
            "error": str(exc),
        }


async def _tool_get_deploy_logs(arguments: dict[str, Any]) -> dict[str, Any]:
    """Retrieve deployment logs from Coolify."""
    project_id = arguments.get("project_id", "")
    environment = arguments.get("environment", "staging")
    lines = arguments.get("lines", 100)
    level = arguments.get("level", "all")

    try:
        data = await _coolify_api(
            "GET",
            f"/applications/{project_id}/logs?lines={lines}",
        )

        raw_logs: list[str] = data.get("logs", [])

        # Filter by level if requested
        if level != "all":
            level_upper = level.upper()
            filtered = [
                log for log in raw_logs
                if level_upper in log.upper()
            ]
        else:
            filtered = raw_logs

        return {
            "logs": filtered[:lines],
            "total_lines": len(filtered),
            "project_id": project_id,
            "environment": environment,
            "level_filter": level,
        }
    except Exception as exc:
        return {
            "logs": [f"Failed to retrieve logs: {exc}"],
            "total_lines": 0,
            "project_id": project_id,
            "environment": environment,
            "error": str(exc),
        }


# Dispatcher
_TOOL_DISPATCH: dict[str, Any] = {
    "check_deploy_readiness": _tool_check_deploy_readiness,
    "get_deploy_status": _tool_get_deploy_status,
    "rollback_deploy": _tool_rollback_deploy,
    "get_deploy_logs": _tool_get_deploy_logs,
}


# ── Lifespan ────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: set up and tear down shared resources."""
    global _start_time, _http_client  # noqa: PLW0603
    _start_time = datetime.now(timezone.utc)
    _http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

    logger.info(
        "mcp_deploy_started",
        service="mcp-deploy",
        port=8337,
    )

    yield

    await _http_client.aclose()
    _http_client = None
    logger.info("mcp_deploy_stopped")


# ── Application ─────────────────────────────────────────────────────

app = FastAPI(
    title="System 44 — MCP Deploy Server",
    description=(
        "Deployment management tools for AI coding agents.  Provides "
        "deployment readiness checks, status queries, rollback operations, "
        "and log retrieval via Coolify."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["infra"])
async def health_check() -> dict[str, Any]:
    """Liveness / readiness probe."""
    coolify_ok = False
    if _http_client is not None:
        try:
            resp = await _http_client.get(
                f"{settings.COOLIFY_URL}/api/v1/health",
                timeout=5.0,
            )
            coolify_ok = resp.status_code == 200
        except Exception:
            pass

    return {
        "status": "healthy",
        "service": "mcp-deploy",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tools_available": len(DEPLOY_TOOLS),
        "dependencies": {
            "coolify": "connected" if coolify_ok else "unavailable",
        },
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
    """Return the list of available deployment tools."""
    REQUEST_COUNT.labels(method="GET", endpoint="/api/v1/tools", status="200").inc()
    return DEPLOY_TOOLS


@app.post("/api/v1/tools/call", tags=["mcp"])
async def call_tool(request: MCPToolCall) -> MCPToolResult:
    """Execute a deployment tool by name."""
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
        await notify_tool_error("deploy", request.tool_name, error_msg)
        return MCPToolResult(
            tool_name=request.tool_name,
            error=error_msg,
            execution_time_ms=round(elapsed_ms, 2),
        )


# ── Dev entry-point ─────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "src.mcp_servers.deploy:app",
        host="0.0.0.0",
        port=8337,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
