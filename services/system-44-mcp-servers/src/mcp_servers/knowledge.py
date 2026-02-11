"""
System 44 — MCP Knowledge Server (port 8338).

Provides knowledge-base query tools accessible to AI coding agents via
the Model Context Protocol.  Tools include semantic search over Qdrant
collections, architecture decision record (ADR) retrieval, code
similarity search, and domain-specific best-practice lookup.
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
    Histogram,
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

logger: structlog.stdlib.BoundLogger = structlog.get_logger("system44.knowledge")

# ── Prometheus metrics ──────────────────────────────────────────────

REGISTRY = CollectorRegistry()
REQUEST_COUNT = Counter(
    "mcp_knowledge_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)
TOOL_CALLS = Counter(
    "mcp_knowledge_tool_calls_total",
    "Total tool invocations",
    ["tool_name", "status"],
    registry=REGISTRY,
)
SEARCH_LATENCY = Histogram(
    "mcp_knowledge_search_latency_seconds",
    "Latency of Qdrant search operations",
    ["collection"],
    registry=REGISTRY,
)
UPTIME_GAUGE = Gauge(
    "mcp_knowledge_uptime_seconds",
    "Seconds since service started",
    registry=REGISTRY,
)

_start_time: datetime | None = None
_http_client: httpx.AsyncClient | None = None

# ── Tool definitions ────────────────────────────────────────────────

KNOWLEDGE_TOOLS: list[MCPToolDefinition] = [
    MCPToolDefinition(
        name="search_knowledge",
        description=(
            "Perform semantic search across Qdrant knowledge-base collections.  "
            "Uses text embedding to find the most relevant documents matching "
            "a natural-language query."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language search query"},
                "collections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["engineering_docs"],
                    "description": "Qdrant collections to search",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["query"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "results": {"type": "array"},
                "total_found": {"type": "integer"},
            },
        },
    ),
    MCPToolDefinition(
        name="get_architecture_decisions",
        description=(
            "Query the architecture decision records (ADR) collection for "
            "relevant decisions.  Returns ADRs matching the query with status, "
            "context, decision, and consequences."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for ADRs"},
                "status": {
                    "type": "string",
                    "enum": ["all", "accepted", "proposed", "deprecated", "superseded"],
                    "default": "all",
                    "description": "Filter by ADR status",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["query"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "adrs": {"type": "array"},
                "total_found": {"type": "integer"},
            },
        },
    ),
    MCPToolDefinition(
        name="find_similar_code",
        description=(
            "Search for code snippets similar to the provided code across the "
            "indexed codebase.  Uses vector similarity to find semantically "
            "related implementations."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code to find similar matches for"},
                "language": {"type": "string", "default": "python"},
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["code"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "similar_code": {"type": "array"},
                "total_found": {"type": "integer"},
            },
        },
    ),
    MCPToolDefinition(
        name="get_best_practices",
        description=(
            "Retrieve domain-specific best practices from the knowledge base.  "
            "Returns curated guidelines, patterns, and recommendations for "
            "the specified domain."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain to query (e.g. security, testing, deployment, api-design, database)",
                },
                "language": {"type": "string", "default": "python"},
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["domain"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "practices": {"type": "array"},
                "total_found": {"type": "integer"},
            },
        },
    ),
]

_TOOL_MAP: dict[str, MCPToolDefinition] = {t.name: t for t in KNOWLEDGE_TOOLS}


# ── Shared helpers ──────────────────────────────────────────────────


async def _get_embedding(text: str) -> list[float]:
    """Generate a text embedding via LiteLLM."""
    assert _http_client is not None
    resp = await _http_client.post(
        f"{settings.LITELLM_URL}/v1/embeddings",
        json={
            "model": "text-embedding-3-small",
            "input": text[:8000],
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


async def _qdrant_search(
    collection: str,
    vector: list[float],
    limit: int = 10,
    score_threshold: float = 0.4,
    filter_conditions: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Perform a vector search on a Qdrant collection."""
    assert _http_client is not None

    payload: dict[str, Any] = {
        "vector": vector,
        "limit": limit,
        "with_payload": True,
        "score_threshold": score_threshold,
    }
    if filter_conditions:
        payload["filter"] = filter_conditions

    search_start = time.perf_counter()
    resp = await _http_client.post(
        f"{settings.QDRANT_URL}/collections/{collection}/points/search",
        json=payload,
        timeout=15.0,
    )
    search_elapsed = time.perf_counter() - search_start
    SEARCH_LATENCY.labels(collection=collection).observe(search_elapsed)

    resp.raise_for_status()
    return resp.json().get("result", [])


async def _llm_chat(system_prompt: str, user_prompt: str) -> str:
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
    resp = await _http_client.post(
        f"{settings.LITELLM_URL}/v1/chat/completions",
        json=payload,
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned


# ── Tool implementations ────────────────────────────────────────────


async def _tool_search_knowledge(arguments: dict[str, Any]) -> dict[str, Any]:
    """Semantic search across Qdrant knowledge-base collections."""
    query = arguments.get("query", "")
    collections = arguments.get("collections", ["engineering_docs"])
    limit = arguments.get("limit", 10)

    try:
        vector = await _get_embedding(query)
    except Exception as exc:
        logger.warning("embedding_generation_failed", error=str(exc))
        return {"results": [], "total_found": 0, "error": f"Embedding failed: {exc}"}

    all_results: list[dict[str, Any]] = []

    for collection in collections:
        try:
            hits = await _qdrant_search(
                collection=collection,
                vector=vector,
                limit=limit,
            )
            for hit in hits:
                payload = hit.get("payload", {})
                all_results.append(
                    {
                        "collection": collection,
                        "score": hit.get("score", 0.0),
                        "title": payload.get("title", payload.get("name", "")),
                        "content": payload.get("content", payload.get("text", ""))[:1000],
                        "metadata": {
                            k: v
                            for k, v in payload.items()
                            if k not in ("content", "text", "title", "name", "vector")
                        },
                    }
                )
        except Exception as exc:
            logger.warning(
                "qdrant_collection_search_failed",
                collection=collection,
                error=str(exc),
            )
            all_results.append(
                {
                    "collection": collection,
                    "score": 0.0,
                    "title": "",
                    "content": "",
                    "metadata": {"error": str(exc)},
                }
            )

    # Sort by score descending and limit
    all_results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    all_results = all_results[:limit]

    return {"results": all_results, "total_found": len(all_results)}


async def _tool_get_architecture_decisions(arguments: dict[str, Any]) -> dict[str, Any]:
    """Query the ADR collection for relevant architecture decisions."""
    query = arguments.get("query", "")
    status_filter = arguments.get("status", "all")
    limit = arguments.get("limit", 10)

    try:
        vector = await _get_embedding(f"architecture decision: {query}")
    except Exception as exc:
        logger.warning("embedding_generation_failed", error=str(exc))
        return {"adrs": [], "total_found": 0, "error": f"Embedding failed: {exc}"}

    # Build Qdrant filter for status
    filter_conditions: dict[str, Any] | None = None
    if status_filter != "all":
        filter_conditions = {
            "must": [
                {
                    "key": "status",
                    "match": {"value": status_filter},
                }
            ]
        }

    try:
        hits = await _qdrant_search(
            collection="architecture_decisions",
            vector=vector,
            limit=limit,
            score_threshold=0.35,
            filter_conditions=filter_conditions,
        )

        adrs = []
        for hit in hits:
            payload = hit.get("payload", {})
            adrs.append(
                {
                    "id": payload.get("adr_id", payload.get("id", "")),
                    "title": payload.get("title", ""),
                    "status": payload.get("status", "unknown"),
                    "context": payload.get("context", ""),
                    "decision": payload.get("decision", ""),
                    "consequences": payload.get("consequences", ""),
                    "date": payload.get("date", ""),
                    "score": hit.get("score", 0.0),
                }
            )

        return {"adrs": adrs, "total_found": len(adrs)}

    except Exception as exc:
        logger.warning("adr_search_failed", error=str(exc))

        # Fallback: try with LLM to synthesize from general knowledge
        try:
            import json

            system_prompt = (
                "You are a software architect.  The user is asking about architecture "
                "decisions.  Based on common best practices and your knowledge, provide "
                "relevant Architecture Decision Records.\n"
                "Return a JSON object with:\n"
                '- "adrs": array of {"id": string, "title": string, "status": "proposed", '
                '"context": string, "decision": string, "consequences": string}\n'
                '- "total_found": integer\n'
                "Return ONLY valid JSON."
            )
            raw = await _llm_chat(system_prompt, query)
            cleaned = _strip_markdown_fences(raw)
            result = json.loads(cleaned)
            return {
                "adrs": result.get("adrs", []),
                "total_found": result.get("total_found", 0),
                "source": "llm_fallback",
            }
        except Exception:
            return {"adrs": [], "total_found": 0, "error": str(exc)}


async def _tool_find_similar_code(arguments: dict[str, Any]) -> dict[str, Any]:
    """Search for code snippets similar to the provided code."""
    code = arguments.get("code", "")
    language = arguments.get("language", "python")
    limit = arguments.get("limit", 5)

    try:
        vector = await _get_embedding(f"[{language}]\n{code[:4000]}")
    except Exception as exc:
        logger.warning("embedding_generation_failed", error=str(exc))
        return {"similar_code": [], "total_found": 0, "error": f"Embedding failed: {exc}"}

    try:
        hits = await _qdrant_search(
            collection="code_snippets",
            vector=vector,
            limit=limit,
            score_threshold=0.5,
        )

        similar_code = []
        for hit in hits:
            payload = hit.get("payload", {})
            similar_code.append(
                {
                    "file_path": payload.get("file_path", payload.get("path", "")),
                    "function_name": payload.get("function_name", payload.get("name", "")),
                    "code": payload.get("code", payload.get("content", payload.get("text", "")))[:2000],
                    "language": payload.get("language", language),
                    "similarity_score": hit.get("score", 0.0),
                    "repository": payload.get("repository", payload.get("repo", "")),
                }
            )

        return {"similar_code": similar_code, "total_found": len(similar_code)}

    except Exception as exc:
        logger.warning("code_similarity_search_failed", error=str(exc))
        return {"similar_code": [], "total_found": 0, "error": str(exc)}


async def _tool_get_best_practices(arguments: dict[str, Any]) -> dict[str, Any]:
    """Retrieve domain-specific best practices from the knowledge base."""
    import json

    domain = arguments.get("domain", "")
    language = arguments.get("language", "python")
    limit = arguments.get("limit", 10)

    # First try Qdrant
    try:
        vector = await _get_embedding(f"best practices for {domain} in {language}")
        hits = await _qdrant_search(
            collection="best_practices",
            vector=vector,
            limit=limit,
            score_threshold=0.4,
        )

        if hits:
            practices = []
            for hit in hits:
                payload = hit.get("payload", {})
                practices.append(
                    {
                        "title": payload.get("title", payload.get("name", "")),
                        "description": payload.get("description", payload.get("content", ""))[:500],
                        "category": payload.get("category", domain),
                        "severity": payload.get("severity", "recommended"),
                        "examples": payload.get("examples", []),
                        "references": payload.get("references", []),
                        "score": hit.get("score", 0.0),
                    }
                )
            return {"practices": practices, "total_found": len(practices)}
    except Exception as exc:
        logger.warning("best_practices_qdrant_failed", error=str(exc))

    # Fallback: use LLM to generate best practices
    system_prompt = (
        f"You are a senior software engineer specialising in {domain}.  "
        f"Provide the most important best practices for {domain} when working "
        f"with {language}.\n\n"
        "Return a JSON object with:\n"
        '- "practices": array of objects with "title" (string), '
        '"description" (string), "category" (string), "severity" '
        '(critical|recommended|optional), "examples" (array of code snippets as strings), '
        '"references" (array of URLs or document names)\n'
        '- "total_found": integer\n'
        "Return ONLY valid JSON, no markdown fencing."
    )

    try:
        raw = await _llm_chat(system_prompt, f"Best practices for {domain} in {language}")
        cleaned = _strip_markdown_fences(raw)
        result = json.loads(cleaned)
        practices = result.get("practices", [])[:limit]
        return {
            "practices": practices,
            "total_found": len(practices),
            "source": "llm_generated",
        }
    except Exception as exc:
        logger.warning("best_practices_llm_failed", error=str(exc))
        return {"practices": [], "total_found": 0, "error": str(exc)}


# Dispatcher
_TOOL_DISPATCH: dict[str, Any] = {
    "search_knowledge": _tool_search_knowledge,
    "get_architecture_decisions": _tool_get_architecture_decisions,
    "find_similar_code": _tool_find_similar_code,
    "get_best_practices": _tool_get_best_practices,
}


# ── Lifespan ────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: set up and tear down shared resources."""
    global _start_time, _http_client  # noqa: PLW0603
    _start_time = datetime.now(timezone.utc)
    _http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))

    logger.info(
        "mcp_knowledge_started",
        service="mcp-knowledge",
        port=8338,
    )

    yield

    await _http_client.aclose()
    _http_client = None
    logger.info("mcp_knowledge_stopped")


# ── Application ─────────────────────────────────────────────────────

app = FastAPI(
    title="System 44 — MCP Knowledge Server",
    description=(
        "Knowledge-base query tools for AI coding agents.  Provides "
        "semantic search, architecture decision lookup, code similarity "
        "search, and domain-specific best practices."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["infra"])
async def health_check() -> dict[str, Any]:
    """Liveness / readiness probe."""
    qdrant_ok = False
    if _http_client is not None:
        try:
            resp = await _http_client.get(
                f"{settings.QDRANT_URL}/collections",
                timeout=5.0,
            )
            qdrant_ok = resp.status_code == 200
        except Exception:
            pass

    return {
        "status": "healthy",
        "service": "mcp-knowledge",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tools_available": len(KNOWLEDGE_TOOLS),
        "dependencies": {
            "qdrant": "connected" if qdrant_ok else "unavailable",
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
    """Return the list of available knowledge tools."""
    REQUEST_COUNT.labels(method="GET", endpoint="/api/v1/tools", status="200").inc()
    return KNOWLEDGE_TOOLS


@app.post("/api/v1/tools/call", tags=["mcp"])
async def call_tool(request: MCPToolCall) -> MCPToolResult:
    """Execute a knowledge tool by name."""
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
        await notify_tool_error("knowledge", request.tool_name, error_msg)
        return MCPToolResult(
            tool_name=request.tool_name,
            error=error_msg,
            execution_time_ms=round(elapsed_ms, 2),
        )


# ── Dev entry-point ─────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "src.mcp_servers.knowledge:app",
        host="0.0.0.0",
        port=8338,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
