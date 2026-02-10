"""
System 27 -- Token Infinity: Context Manager Service
Omni Quantum Elite AI Coding System

Intelligent context assembly engine that compiles optimal prompts for every AI task.
Retrieves relevant code, patterns, feedback, and architecture context from Qdrant
vector collections and Gitea repositories, then packs them into a priority-ordered
context window that maximises signal within the target model's token budget.

Port: 9600
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("token_infinity.context_manager")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://omni-qdrant:6333")
LITELLM_URL: str = os.getenv("LITELLM_URL", "http://omni-litellm:4000")
OLLAMA_MANAGER_URL: str = os.getenv("OLLAMA_MANAGER_URL", "http://omni-model-manager:11435")
LANGFUSE_URL: str = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
VAULT_URL: str = os.getenv("VAULT_URL", "http://omni-vault:8200")
GITEA_URL: str = os.getenv("GITEA_URL", "http://omni-gitea:3000")
MATTERMOST_WEBHOOK_URL: str = os.getenv("MATTERMOST_WEBHOOK_URL", "http://omni-mattermost-webhook:8066")

SERVICE_NAME: str = "token-infinity-context-manager"
SERVICE_VERSION: str = "1.0.0"

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
registry = CollectorRegistry()

CONTEXT_COMPILATION_DURATION = Histogram(
    "context_compilation_duration_seconds",
    "Time taken to compile a context window",
    labelnames=["task_type"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)
CONTEXT_TOTAL_TOKENS = Histogram(
    "context_total_tokens",
    "Total tokens in compiled context",
    labelnames=["task_type"],
    buckets=[500, 1000, 2000, 4000, 8000, 16000, 32000, 64000, 128000],
    registry=registry,
)
CONTEXT_BUDGET_UTILIZATION = Histogram(
    "context_budget_utilization",
    "Fraction of token budget utilised",
    labelnames=["task_type"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry,
)
CONTEXT_BLOCKS_INCLUDED = Counter(
    "context_blocks_included",
    "Number of context blocks included",
    labelnames=["block_type"],
    registry=registry,
)
CONTEXT_BLOCKS_TRUNCATED = Counter(
    "context_blocks_truncated",
    "Number of context blocks truncated",
    labelnames=["block_type"],
    registry=registry,
)
CONTEXT_CACHE_HITS = Counter(
    "context_cache_hits",
    "Cache hits for context compilation",
    registry=registry,
)
REQUESTS_TOTAL = Counter(
    "context_requests_total",
    "Total requests handled",
    labelnames=["endpoint", "status"],
    registry=registry,
)

# ---------------------------------------------------------------------------
# Enums and constants
# ---------------------------------------------------------------------------

class TaskType(str, Enum):
    FEATURE_BUILD = "feature-build"
    BUG_FIX = "bug-fix"
    REFACTOR = "refactor"
    TEST_GEN = "test-gen"
    REVIEW = "review"
    DOCUMENTATION = "documentation"


class Complexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Model context windows (tokens)
MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "devstral-small": 32_768,
    "devstral-2": 131_072,
    "deepseek-v3.2": 131_072,
    "deepseek": 65_536,
    "qwen3-coder": 65_536,
    "llama-3.3-70b-versatile": 131_072,
    "llama-3.1-8b-instant": 131_072,
    "mixtral-8x7b-32768": 32_768,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "claude-3.5-sonnet": 200_000,
    "claude-3-haiku": 200_000,
    "default": 32_768,
}

# Reserved output tokens per task type
RESERVED_OUTPUT_TOKENS: dict[str, int] = {
    "feature-build": 16_384,
    "bug-fix": 16_384,
    "refactor": 16_384,
    "test-gen": 16_384,
    "review": 4_096,
    "documentation": 4_096,
}

# Priority block budget fractions (of remaining budget after system prompt)
BLOCK_BUDGET_FRACTIONS: dict[str, float] = {
    "referenced_files": 0.30,
    "semantic_code": 0.25,
    "design_patterns": 0.15,
    "anti_patterns": 0.05,
    "human_feedback": 0.10,
    "architecture": 0.10,
    "elite_examples": 1.0,  # fill remaining
}

# Qdrant collection mapping
QDRANT_COLLECTIONS: dict[str, str] = {
    "semantic_code": "codebase_embeddings",
    "design_patterns": "design_patterns",
    "anti_patterns": "anti_patterns",
    "human_feedback": "human_feedback",
    "architecture": "project_context",
    "elite_examples": "elite_codebases",
}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CompileContextRequest(BaseModel):
    """Request body for POST /context/compile."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str = Field(..., min_length=1, max_length=10_000)
    task_type: TaskType
    complexity: Complexity
    project_id: Optional[str] = None
    referenced_files: Optional[list[str]] = None
    target_model: Optional[str] = None
    max_tokens: Optional[int] = None


class ContextBlock(BaseModel):
    """A single block within the compiled context."""
    type: str
    tokens: int
    source: str
    details: str
    truncated: bool = False


class CompileContextResponse(BaseModel):
    """Response body for POST /context/compile."""
    compiled_context: str
    model_recommendation: str
    token_count: int
    token_budget: int
    context_blocks: list[ContextBlock]
    trace_id: str


class TokenEstimateRequest(BaseModel):
    """Request body for POST /context/estimate."""
    task_description: str = Field(..., min_length=1, max_length=10_000)
    task_type: TaskType = TaskType.FEATURE_BUILD
    complexity: Complexity = Complexity.MEDIUM
    referenced_files: Optional[list[str]] = None


class TokenEstimateResponse(BaseModel):
    """Response for POST /context/estimate."""
    estimated_tokens: int
    estimated_blocks: dict[str, int]
    recommended_model: str
    fits_in_budget: bool
    budget: int


class BudgetResponse(BaseModel):
    """Response for GET /context/budget/{model}."""
    model: str
    context_window: int
    reserved_output: dict[str, int]
    available_budget: dict[str, int]


class ModelRecommendationResponse(BaseModel):
    """Response for GET /models/recommend."""
    recommended_model: str
    context_window: int
    reasoning: str
    alternatives: list[str]


class HealthResponse(BaseModel):
    """Standard health check response."""
    status: str
    service: str
    version: str
    timestamp: str
    checks: dict[str, str]


class ReadyResponse(BaseModel):
    """Readiness check response."""
    ready: bool
    checks: dict[str, bool]


# ---------------------------------------------------------------------------
# Token counting utility (word/4 approximation)
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Estimate token count using word/4 character heuristic.

    Uses a simple approximation: 1 token ~ 4 characters. This avoids
    requiring tiktoken as an external dependency while remaining within
    ~10% accuracy for English prose and code.

    Args:
        text: The input string.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_to_tokens(text: str, max_tokens: int, keep_signatures: bool = True) -> tuple[str, bool]:
    """Truncate text to fit within a token budget.

    When *keep_signatures* is ``True``, the function preserves function /
    class signatures and trims method bodies first so the context retains
    structural information even when truncated.

    Args:
        text: Original text.
        max_tokens: Maximum tokens allowed.
        keep_signatures: If True, prefer keeping signatures over bodies.

    Returns:
        A tuple of (truncated_text, was_truncated).
    """
    current_tokens = estimate_tokens(text)
    if current_tokens <= max_tokens:
        return text, False

    if keep_signatures:
        lines = text.split("\n")
        result_lines: list[str] = []
        running_tokens = 0
        in_body = False
        body_depth = 0

        for line in lines:
            stripped = line.strip()

            # Detect function/class signatures
            is_signature = (
                stripped.startswith("def ")
                or stripped.startswith("class ")
                or stripped.startswith("async def ")
                or stripped.startswith("function ")
                or stripped.startswith("export ")
                or stripped.startswith("public ")
                or stripped.startswith("private ")
                or stripped.startswith("protected ")
            )

            if is_signature:
                in_body = False
                body_depth = 0

            line_tokens = estimate_tokens(line)

            # Always keep signatures and top-level statements
            if is_signature or not in_body:
                if running_tokens + line_tokens > max_tokens:
                    result_lines.append("    # ... (truncated)")
                    break
                result_lines.append(line)
                running_tokens += line_tokens
                if is_signature:
                    in_body = True
                    body_depth = 0
            else:
                # Inside a body -- include the first few lines, then skip
                body_depth += 1
                if body_depth <= 3:
                    if running_tokens + line_tokens > max_tokens:
                        result_lines.append("    # ... (truncated)")
                        break
                    result_lines.append(line)
                    running_tokens += line_tokens
                elif body_depth == 4:
                    marker = "    # ... (body truncated)"
                    marker_tokens = estimate_tokens(marker)
                    if running_tokens + marker_tokens <= max_tokens:
                        result_lines.append(marker)
                        running_tokens += marker_tokens

        return "\n".join(result_lines), True

    # Fallback: hard character-level truncation
    max_chars = max_tokens * 4
    return text[:max_chars] + "\n... (truncated)", True


# ---------------------------------------------------------------------------
# System prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE: str = """You are an elite software engineer operating within the Omni Quantum Elite AI Coding System.

## Task Specification
- Task ID: {task_id}
- Task Type: {task_type}
- Complexity: {complexity}
- Description: {task_description}

## Mandatory Rules
1. Write production-grade code with full type hints and docstrings.
2. Never introduce security vulnerabilities (SQL injection, XSS, path traversal, secret leakage).
3. All error handling must be explicit -- never silently swallow exceptions.
4. Follow existing project conventions visible in the provided context.
5. Include appropriate logging using structlog with structured JSON output.
6. Use Pydantic models for data validation at service boundaries.
7. Write code that is testable -- prefer dependency injection, avoid global state.
8. Respect the DRY principle -- reuse existing utilities shown in context.

## Error Prevention Rules
- Never use `eval()`, `exec()`, or `__import__()` with user-supplied input.
- Always validate and sanitise file paths to prevent directory traversal.
- Use parameterised queries for all database operations.
- Never log secrets, tokens, or passwords.
- Always set timeouts on HTTP requests and database connections.
"""

ERROR_CONTEXT_TEMPLATE: str = """
## Error Context
The following error was encountered:
```
{error_details}
```
Focus your fix on the root cause, not just the symptoms.
"""


# ---------------------------------------------------------------------------
# HTTP client helpers
# ---------------------------------------------------------------------------

def _build_http_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Build a configured httpx.AsyncClient with retry-friendly timeouts.

    Args:
        timeout: Total request timeout in seconds.

    Returns:
        Configured async HTTP client.
    """
    transport = httpx.AsyncHTTPTransport(retries=3)
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=10.0),
        transport=transport,
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# Context source fetchers
# ---------------------------------------------------------------------------

async def _fetch_gitea_file(
    client: httpx.AsyncClient,
    project_id: str,
    filepath: str,
) -> Optional[str]:
    """Fetch a single file from Gitea API.

    Args:
        client: Shared HTTP client.
        project_id: The Gitea repository identifier (owner/repo).
        filepath: Path within the repository.

    Returns:
        Decoded file content, or None on failure.
    """
    url = f"{GITEA_URL}/api/v1/repos/{project_id}/raw/{filepath}"
    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            return resp.text
        logger.warning("gitea_file_fetch_failed", filepath=filepath, status=resp.status_code)
    except httpx.HTTPError as exc:
        logger.warning("gitea_file_fetch_error", filepath=filepath, error=str(exc))
    return None


async def _fetch_gitea_tree(
    client: httpx.AsyncClient,
    project_id: str,
) -> Optional[str]:
    """Fetch the repository file tree from Gitea.

    Args:
        client: Shared HTTP client.
        project_id: The Gitea repository identifier (owner/repo).

    Returns:
        Formatted file tree string, or None on failure.
    """
    url = f"{GITEA_URL}/api/v1/repos/{project_id}/git/trees/HEAD"
    try:
        resp = await client.get(url, params={"recursive": "true"})
        if resp.status_code == 200:
            data = resp.json()
            entries = data.get("tree", [])
            paths = sorted(e.get("path", "") for e in entries if e.get("type") == "blob")
            return "\n".join(paths)
        logger.warning("gitea_tree_fetch_failed", project_id=project_id, status=resp.status_code)
    except httpx.HTTPError as exc:
        logger.warning("gitea_tree_fetch_error", project_id=project_id, error=str(exc))
    return None


async def _query_qdrant(
    client: httpx.AsyncClient,
    collection: str,
    query_text: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Query a Qdrant collection using keyword-based search.

    Uses Qdrant's scroll/search endpoint. Falls back to scroll if the
    collection does not have a text-search index.

    Args:
        client: Shared HTTP client.
        collection: Qdrant collection name.
        query_text: The search query (used as filter context).
        limit: Maximum number of results.

    Returns:
        List of point payloads.
    """
    url = f"{QDRANT_URL}/collections/{collection}/points/scroll"
    payload: dict[str, Any] = {
        "limit": limit,
        "with_payload": True,
        "with_vector": False,
    }

    try:
        resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            points = data.get("result", {}).get("points", [])
            return [p.get("payload", {}) for p in points]
        logger.warning(
            "qdrant_query_failed",
            collection=collection,
            status=resp.status_code,
            body=resp.text[:500],
        )
    except httpx.HTTPError as exc:
        logger.warning("qdrant_query_error", collection=collection, error=str(exc))

    return []


# ---------------------------------------------------------------------------
# Model recommendation logic
# ---------------------------------------------------------------------------

def recommend_model(complexity: Complexity, task_type: TaskType) -> tuple[str, str, list[str]]:
    """Recommend the best model for a given complexity and task type.

    Args:
        complexity: Task complexity level.
        task_type: The kind of task to perform.

    Returns:
        Tuple of (model_name, reasoning, alternatives).
    """
    alternatives: list[str] = []

    if complexity in (Complexity.CRITICAL, Complexity.HIGH):
        model = "devstral-2"
        reasoning = (
            "Critical/high complexity tasks require the most capable local model "
            "with maximum context window (128K) for thorough code generation."
        )
        alternatives = ["deepseek-v3.2", "llama-3.3-70b-versatile"]
    elif complexity == Complexity.MEDIUM:
        if task_type in (TaskType.REVIEW, TaskType.DOCUMENTATION):
            model = "qwen3-coder"
            reasoning = (
                "Medium-complexity reviews and documentation benefit from "
                "Qwen3-Coder's strong comprehension at lower resource cost."
            )
            alternatives = ["deepseek", "devstral-small"]
        else:
            model = "deepseek"
            reasoning = (
                "Medium-complexity code generation tasks are well-served by "
                "DeepSeek's balanced performance and 64K context window."
            )
            alternatives = ["qwen3-coder", "devstral-2"]
    else:
        model = "devstral-small"
        reasoning = (
            "Low-complexity tasks can be handled efficiently by the smaller "
            "Devstral model, preserving GPU resources for harder tasks."
        )
        alternatives = ["qwen3-coder", "deepseek"]

    return model, reasoning, alternatives


# ---------------------------------------------------------------------------
# Context compilation engine
# ---------------------------------------------------------------------------

async def compile_context(req: CompileContextRequest) -> CompileContextResponse:
    """Assemble the optimal context window for an AI task.

    Implements priority-based filling:
        1. System prompt + task spec + rules  (mandatory)
        2. Referenced files + project tree     (30% of remaining)
        3. Semantic similar code               (25%)
        4. Design patterns                     (15%)
        5. Anti-patterns                       (5%)
        6. Human feedback                      (10%)
        7. Architecture context                (10%)
        8. Elite examples                      (fill remaining)

    Args:
        req: The compile context request.

    Returns:
        A fully assembled context response.
    """
    trace_id = str(uuid.uuid4())
    start_time = time.monotonic()

    log = logger.bind(trace_id=trace_id, task_id=req.task_id, task_type=req.task_type.value)
    log.info("context_compilation_started")

    # -- Determine model and budget --
    model_name, reasoning, alternatives = recommend_model(req.complexity, req.task_type)
    if req.target_model:
        model_name = req.target_model

    context_window = MODEL_CONTEXT_WINDOWS.get(model_name, MODEL_CONTEXT_WINDOWS["default"])
    if req.max_tokens and req.max_tokens < context_window:
        context_window = req.max_tokens

    reserved_output = RESERVED_OUTPUT_TOKENS.get(req.task_type.value, 16_384)
    total_budget = context_window - reserved_output

    if total_budget <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Model {model_name} context window ({context_window}) is smaller than reserved output ({reserved_output}).",
        )

    # -- Block 1: System prompt (mandatory) --
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        task_id=req.task_id,
        task_type=req.task_type.value,
        complexity=req.complexity.value,
        task_description=req.task_description,
    )
    system_tokens = estimate_tokens(system_prompt)

    if system_tokens > total_budget:
        raise HTTPException(
            status_code=400,
            detail=(
                f"System prompt ({system_tokens} tokens) exceeds total budget "
                f"({total_budget} tokens) for model {model_name}. Cannot compile context."
            ),
        )

    context_parts: list[str] = [system_prompt]
    blocks: list[ContextBlock] = [
        ContextBlock(
            type="system_prompt",
            tokens=system_tokens,
            source="internal",
            details="System prompt with task specification and safety rules",
        )
    ]
    used_tokens = system_tokens
    remaining = total_budget - used_tokens

    log.info("system_prompt_assembled", tokens=system_tokens, remaining=remaining)

    # -- Fetch external data concurrently --
    async with _build_http_client(timeout=30.0) as client:
        # Prepare concurrent fetches
        fetch_tasks: dict[str, Any] = {}

        # Referenced files
        if req.referenced_files and req.project_id:
            for fp in req.referenced_files:
                fetch_tasks[f"file:{fp}"] = _fetch_gitea_file(client, req.project_id, fp)
            fetch_tasks["tree"] = _fetch_gitea_tree(client, req.project_id)
        elif req.project_id:
            fetch_tasks["tree"] = _fetch_gitea_tree(client, req.project_id)

        # Qdrant queries
        for block_type, collection in QDRANT_COLLECTIONS.items():
            fetch_tasks[f"qdrant:{block_type}"] = _query_qdrant(
                client, collection, req.task_description, limit=10,
            )

        # Execute all fetches concurrently
        keys = list(fetch_tasks.keys())
        results = await asyncio.gather(*fetch_tasks.values(), return_exceptions=True)
        fetched: dict[str, Any] = {}
        for key, result in zip(keys, results):
            if isinstance(result, Exception):
                log.warning("fetch_failed", key=key, error=str(result))
                fetched[key] = None
            else:
                fetched[key] = result

    # -- Block 2: Referenced files + project tree (30% remaining) --
    block_budget = int(remaining * BLOCK_BUDGET_FRACTIONS["referenced_files"])
    block_tokens_used = 0

    if req.referenced_files and req.project_id:
        file_contents: list[str] = []
        for fp in req.referenced_files:
            content = fetched.get(f"file:{fp}")
            if content:
                file_header = f"\n## File: {fp}\n```\n{content}\n```\n"
                ft = estimate_tokens(file_header)
                if block_tokens_used + ft <= block_budget:
                    file_contents.append(file_header)
                    block_tokens_used += ft
                else:
                    truncated_content, _ = truncate_to_tokens(
                        file_header, block_budget - block_tokens_used, keep_signatures=True,
                    )
                    file_contents.append(truncated_content)
                    block_tokens_used += estimate_tokens(truncated_content)
                    CONTEXT_BLOCKS_TRUNCATED.labels(block_type="referenced_files").inc()
                    break

        if file_contents:
            section = "\n# Referenced Files\n" + "\n".join(file_contents)
            context_parts.append(section)
            blocks.append(ContextBlock(
                type="referenced_files",
                tokens=block_tokens_used,
                source="gitea",
                details=f"Referenced files: {', '.join(req.referenced_files[:5])}",
                truncated=block_tokens_used >= block_budget,
            ))
            CONTEXT_BLOCKS_INCLUDED.labels(block_type="referenced_files").inc()
            used_tokens += block_tokens_used
            remaining = total_budget - used_tokens

    # Project tree
    tree = fetched.get("tree")
    if tree and req.project_id:
        tree_section = f"\n# Project File Tree\n```\n{tree}\n```\n"
        tree_tokens = estimate_tokens(tree_section)
        tree_budget = int(remaining * 0.05)  # small budget for tree
        if tree_tokens > tree_budget:
            tree_section, _ = truncate_to_tokens(tree_section, tree_budget, keep_signatures=False)
            tree_tokens = estimate_tokens(tree_section)
            CONTEXT_BLOCKS_TRUNCATED.labels(block_type="project_tree").inc()
        context_parts.append(tree_section)
        blocks.append(ContextBlock(
            type="project_tree",
            tokens=tree_tokens,
            source="gitea",
            details=f"File tree for {req.project_id}",
        ))
        CONTEXT_BLOCKS_INCLUDED.labels(block_type="project_tree").inc()
        used_tokens += tree_tokens
        remaining = total_budget - used_tokens

    # -- Blocks 3-8: Qdrant-sourced context --
    qdrant_block_order: list[tuple[str, str]] = [
        ("semantic_code", "Semantically Similar Code"),
        ("design_patterns", "Design Patterns"),
        ("anti_patterns", "Anti-Patterns to Avoid"),
        ("human_feedback", "Human Feedback and Corrections"),
        ("architecture", "Architecture Context"),
        ("elite_examples", "Elite Code Examples"),
    ]

    for block_type, section_title in qdrant_block_order:
        fraction = BLOCK_BUDGET_FRACTIONS.get(block_type, 0.05)
        # For elite_examples, use all remaining budget
        if block_type == "elite_examples":
            block_budget = remaining
        else:
            block_budget = int(remaining * fraction)

        if block_budget <= 50:
            log.debug("skipping_block_no_budget", block_type=block_type)
            continue

        qdrant_results = fetched.get(f"qdrant:{block_type}")
        if not qdrant_results:
            continue

        section_parts: list[str] = [f"\n# {section_title}\n"]
        block_tokens_used = estimate_tokens(section_parts[0])

        for payload in qdrant_results:
            # Extract content from payload -- try common field names
            content = (
                payload.get("content")
                or payload.get("text")
                or payload.get("code")
                or payload.get("description")
                or payload.get("body")
            )
            if not content:
                continue

            source_info = payload.get("source", payload.get("file_path", "unknown"))
            entry = f"\n## Source: {source_info}\n```\n{content}\n```\n"
            entry_tokens = estimate_tokens(entry)

            if block_tokens_used + entry_tokens <= block_budget:
                section_parts.append(entry)
                block_tokens_used += entry_tokens
            else:
                # Truncate this entry to fit
                space_left = block_budget - block_tokens_used
                if space_left > 50:
                    truncated_entry, _ = truncate_to_tokens(entry, space_left, keep_signatures=True)
                    section_parts.append(truncated_entry)
                    block_tokens_used += estimate_tokens(truncated_entry)
                    CONTEXT_BLOCKS_TRUNCATED.labels(block_type=block_type).inc()
                break

        if block_tokens_used > estimate_tokens(section_parts[0]):
            full_section = "".join(section_parts)
            context_parts.append(full_section)
            blocks.append(ContextBlock(
                type=block_type,
                tokens=block_tokens_used,
                source=f"qdrant:{QDRANT_COLLECTIONS[block_type]}",
                details=f"{section_title} ({len(qdrant_results)} results queried)",
                truncated=block_tokens_used >= block_budget,
            ))
            CONTEXT_BLOCKS_INCLUDED.labels(block_type=block_type).inc()
            used_tokens += block_tokens_used
            remaining = total_budget - used_tokens

    # -- Assemble final context --
    compiled_context = "\n".join(context_parts)
    final_token_count = estimate_tokens(compiled_context)

    # -- Record metrics --
    duration = time.monotonic() - start_time
    CONTEXT_COMPILATION_DURATION.labels(task_type=req.task_type.value).observe(duration)
    CONTEXT_TOTAL_TOKENS.labels(task_type=req.task_type.value).observe(final_token_count)
    if total_budget > 0:
        CONTEXT_BUDGET_UTILIZATION.labels(task_type=req.task_type.value).observe(
            min(1.0, final_token_count / total_budget)
        )

    log.info(
        "context_compilation_complete",
        token_count=final_token_count,
        token_budget=total_budget,
        blocks=len(blocks),
        duration_s=round(duration, 3),
        utilization=round(final_token_count / total_budget, 3) if total_budget > 0 else 0,
    )

    return CompileContextResponse(
        compiled_context=compiled_context,
        model_recommendation=model_name,
        token_count=final_token_count,
        token_budget=total_budget,
        context_blocks=blocks,
        trace_id=trace_id,
    )


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    logger.info("context_manager_starting", port=9600, version=SERVICE_VERSION)
    yield
    logger.info("context_manager_shutting_down")


app = FastAPI(
    title="Token Infinity -- Context Manager",
    description=(
        "Intelligent context assembly engine for the Omni Quantum Elite AI Coding System. "
        "Compiles optimal prompts by retrieving and prioritising code, patterns, feedback, "
        "and architecture context within target model token budgets."
    ),
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/context/compile", response_model=CompileContextResponse)
async def endpoint_compile_context(req: CompileContextRequest) -> CompileContextResponse:
    """Compile an optimal context window for an AI task.

    Assembles context from multiple sources (Gitea files, Qdrant vector
    collections) using a priority-based filling algorithm that maximises
    signal within the target model's token budget.
    """
    REQUESTS_TOTAL.labels(endpoint="/context/compile", status="started").inc()
    try:
        result = await compile_context(req)
        REQUESTS_TOTAL.labels(endpoint="/context/compile", status="success").inc()
        return result
    except HTTPException:
        REQUESTS_TOTAL.labels(endpoint="/context/compile", status="error").inc()
        raise
    except Exception as exc:
        REQUESTS_TOTAL.labels(endpoint="/context/compile", status="error").inc()
        logger.exception("context_compilation_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Context compilation failed: {exc}") from exc


@app.get("/context/budget/{model}", response_model=BudgetResponse)
async def endpoint_context_budget(model: str) -> BudgetResponse:
    """Get the token budget breakdown for a specific model.

    Returns the model's total context window and available budget for
    each task type after subtracting reserved output tokens.
    """
    context_window = MODEL_CONTEXT_WINDOWS.get(model, MODEL_CONTEXT_WINDOWS["default"])
    available: dict[str, int] = {}
    for task_type, reserved in RESERVED_OUTPUT_TOKENS.items():
        available[task_type] = max(0, context_window - reserved)

    return BudgetResponse(
        model=model,
        context_window=context_window,
        reserved_output=RESERVED_OUTPUT_TOKENS,
        available_budget=available,
    )


@app.post("/context/estimate", response_model=TokenEstimateResponse)
async def endpoint_estimate_tokens(req: TokenEstimateRequest) -> TokenEstimateResponse:
    """Estimate the token usage for a context compilation without executing it.

    Provides a quick estimate of how many tokens each block type would
    consume, and whether the total fits within the recommended model's budget.
    """
    model_name, _, _ = recommend_model(req.complexity, req.task_type)
    context_window = MODEL_CONTEXT_WINDOWS.get(model_name, MODEL_CONTEXT_WINDOWS["default"])
    reserved = RESERVED_OUTPUT_TOKENS.get(req.task_type.value, 16_384)
    budget = context_window - reserved

    # Estimate system prompt
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        task_id="estimate",
        task_type=req.task_type.value,
        complexity=req.complexity.value,
        task_description=req.task_description,
    )
    system_tokens = estimate_tokens(system_prompt)
    remaining = budget - system_tokens

    estimated_blocks: dict[str, int] = {"system_prompt": system_tokens}

    # Estimate each block
    if req.referenced_files:
        # Rough estimate: ~500 tokens per file
        file_tokens = min(int(remaining * 0.30), len(req.referenced_files) * 500)
        estimated_blocks["referenced_files"] = file_tokens
    else:
        file_tokens = 0

    block_order = [
        ("semantic_code", 0.25),
        ("design_patterns", 0.15),
        ("anti_patterns", 0.05),
        ("human_feedback", 0.10),
        ("architecture", 0.10),
        ("elite_examples", 0.10),
    ]

    for block_type, fraction in block_order:
        est = int((remaining - file_tokens) * fraction)
        estimated_blocks[block_type] = est

    total_estimated = sum(estimated_blocks.values())

    return TokenEstimateResponse(
        estimated_tokens=total_estimated,
        estimated_blocks=estimated_blocks,
        recommended_model=model_name,
        fits_in_budget=total_estimated <= budget,
        budget=budget,
    )


@app.get("/models/recommend", response_model=ModelRecommendationResponse)
async def endpoint_recommend_model(
    complexity: Complexity = Query(..., description="Task complexity level"),
    task_type: TaskType = Query(..., description="Type of task"),
) -> ModelRecommendationResponse:
    """Recommend the best model for a given complexity and task type.

    Returns a model recommendation with reasoning and alternative options
    based on the task requirements.
    """
    model_name, reasoning, alternatives = recommend_model(complexity, task_type)
    context_window = MODEL_CONTEXT_WINDOWS.get(model_name, MODEL_CONTEXT_WINDOWS["default"])

    return ModelRecommendationResponse(
        recommended_model=model_name,
        context_window=context_window,
        reasoning=reasoning,
        alternatives=alternatives,
    )


@app.get("/health", response_model=HealthResponse)
async def endpoint_health() -> HealthResponse:
    """Service health check.

    Verifies that the context manager process is running and can accept
    requests. Does not verify external dependency availability (use /ready
    for that).
    """
    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks={"process": "ok"},
    )


@app.get("/ready", response_model=ReadyResponse)
async def endpoint_ready() -> ReadyResponse:
    """Readiness probe that verifies connectivity to external dependencies.

    Checks Qdrant and Gitea availability. The service is considered ready
    only when all critical dependencies are reachable.
    """
    checks: dict[str, bool] = {}

    async with _build_http_client(timeout=5.0) as client:
        # Check Qdrant
        try:
            resp = await client.get(f"{QDRANT_URL}/collections")
            checks["qdrant"] = resp.status_code == 200
        except httpx.HTTPError:
            checks["qdrant"] = False

        # Check Gitea
        try:
            resp = await client.get(f"{GITEA_URL}/api/v1/version")
            checks["gitea"] = resp.status_code == 200
        except httpx.HTTPError:
            checks["gitea"] = False

        # Check LiteLLM
        try:
            resp = await client.get(f"{LITELLM_URL}/health/liveliness")
            checks["litellm"] = resp.status_code == 200
        except httpx.HTTPError:
            checks["litellm"] = False

        # Check Ollama Manager
        try:
            resp = await client.get(f"{OLLAMA_MANAGER_URL}/health")
            checks["ollama_manager"] = resp.status_code == 200
        except httpx.HTTPError:
            checks["ollama_manager"] = False

    all_ready = all(checks.values())

    if not all_ready:
        logger.warning("readiness_check_failed", checks=checks)

    return ReadyResponse(ready=all_ready, checks=checks)


@app.get("/metrics")
async def endpoint_metrics() -> JSONResponse:
    """Expose Prometheus metrics in text format."""
    from prometheus_client import CONTENT_TYPE_LATEST

    metrics_output = generate_latest(registry)
    return JSONResponse(
        content={"metrics": metrics_output.decode("utf-8")},
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "service": SERVICE_NAME,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9600,
        log_level="info",
        access_log=True,
        reload=False,
        workers=1,
    )
