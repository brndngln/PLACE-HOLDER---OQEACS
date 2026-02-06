#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                       CONTEXT COMPILER SERVICE                              ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This microservice aggregates relevant context for AI agents. Given a task   ║
║ description and optional token budget, it gathers code snippets, known      ║
║ patterns, anti‑patterns, tool descriptions and error history from various   ║
║ sources such as the local codebase, Qdrant collections and internal logs.   ║
║ The service prioritizes relevance and manages the token budget across       ║
║ sections, returning a curated context rather than a raw repository dump.    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

# ════════════════════════════════════════════════════════════════════
# DATA MODELS AND ENUMS
# ════════════════════════════════════════════════════════════════════


class Section(str):
    """Enumeration of context sections."""

    CODE = "code"
    PATTERNS = "patterns"
    ANTI_PATTERNS = "anti_patterns"
    TOOLS = "tools"
    ERRORS = "errors"


@dataclasses.dataclass
class ContextPiece:
    """Internal representation of a context section."""

    section: Section
    content: str


class ContextRequest(BaseModel):
    """Request model for context compilation."""

    task_description: str = Field(..., description="Natural language description of the task")
    max_tokens: Optional[int] = Field(None, ge=100, le=8000, description="Maximum token budget for context")


class ContextResponse(BaseModel):
    """Response model containing assembled context."""

    context: str = Field(..., description="Curated context string")
    token_count: int = Field(..., description="Approximate token count of the returned context")
    generated_at: datetime = Field(..., description="Timestamp when context was compiled")


# ════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ════════════════════════════════════════════════════════════════════


def approximate_tokens(text: str) -> int:
    """Approximate token count by assuming average 4 characters per token."""
    return max(1, len(text) // 4)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate the text to fit within the given token limit."""
    # Roughly convert tokens to characters
    max_chars = max_tokens * 4
    return text[:max_chars]


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """Extract simple keywords from task description for searching code."""
    # Very naive keyword extraction: take unique lowercased words longer than 3 characters
    words = re.findall(r"\b\w{4,}\b", text.lower())
    unique = list(dict.fromkeys(words))
    return unique[:max_keywords]


# ════════════════════════════════════════════════════════════════════
# SERVICE LAYER
# ════════════════════════════════════════════════════════════════════


class ContextCompilerService:
    """Service responsible for assembling context from multiple sources."""

    def __init__(self, qdrant_host: str, qdrant_port: int, code_root: str) -> None:
        self.qdrant = AsyncQdrantClient(host=qdrant_host, port=qdrant_port)
        self.code_root = code_root
        self.logger = structlog.get_logger(__name__).bind(component="context_compiler_service")
        # Metrics
        self.request_count = Counter(
            "context_compiler_requests_total",
            "Total number of context compilation requests",
        )
        self.request_latency = Histogram(
            "context_compiler_latency_seconds",
            "Latency of context compilation requests",
            buckets=(0.1, 0.25, 0.5, 1, 2, 5),
        )

    async def compile_context(self, task_description: str, max_tokens: Optional[int]) -> ContextResponse:
        self.request_count.inc()
        timer = self.request_latency.time()
        async with timer:
            # Default token budget if not provided
            token_budget = max_tokens or 2000
            # Extract keywords for code search
            keywords = extract_keywords(task_description)
            # Gather content pieces concurrently
            pieces = await asyncio.gather(
                self._gather_code(keywords),
                self._gather_patterns(keywords),
                self._gather_anti_patterns(keywords),
                self._gather_tools(keywords),
                self._gather_errors(keywords),
            )
            # Flatten list of lists
            all_pieces: List[ContextPiece] = []
            for section_pieces in pieces:
                all_pieces.extend(section_pieces)
            # Prioritize sections and allocate tokens
            # We allocate token budget as: code 40%, patterns 20%, tools 20%, anti_patterns 10%, errors 10%
            budget_map = {
                Section.CODE: int(token_budget * 0.4),
                Section.PATTERNS: int(token_budget * 0.2),
                Section.TOOLS: int(token_budget * 0.2),
                Section.ANTI_PATTERNS: int(token_budget * 0.1),
                Section.ERRORS: int(token_budget * 0.1),
            }
            compiled_sections: Dict[Section, str] = {sec: "" for sec in Section}
            for piece in all_pieces:
                remaining_tokens = budget_map[piece.section] - approximate_tokens(compiled_sections[piece.section])
                if remaining_tokens <= 0:
                    continue
                truncated = truncate_to_tokens(piece.content, remaining_tokens)
                compiled_sections[piece.section] += truncated + "\n\n"
            # Build final context string with headers
            context_parts = []
            for sec in [Section.CODE, Section.PATTERNS, Section.ANTI_PATTERNS, Section.TOOLS, Section.ERRORS]:
                if compiled_sections[sec].strip():
                    header = sec.replace("_", " ").title()
                    context_parts.append(f"## {header}\n{compiled_sections[sec].strip()}")
            final_context = "\n\n".join(context_parts)
            return ContextResponse(
                context=final_context,
                token_count=approximate_tokens(final_context),
                generated_at=datetime.utcnow(),
            )

    async def _gather_code(self, keywords: List[str]) -> List[ContextPiece]:
        """Search local codebase for relevant snippets matching keywords."""
        pieces: List[ContextPiece] = []
        if not keywords:
            return pieces
        try:
            # Walk through .py files and search for keyword occurrences
            for dirpath, _, filenames in os.walk(self.code_root):
                for fname in filenames:
                    if not fname.endswith(".py"):
                        continue
                    file_path = os.path.join(dirpath, fname)
                    try:
                        with open(file_path, "r", encoding="utf-8") as fh:
                            content = fh.read()
                        for kw in keywords:
                            if kw in content:
                                # Extract up to first 5 lines around keyword
                                lines = content.splitlines()
                                for idx, line in enumerate(lines):
                                    if kw in line:
                                        start = max(0, idx - 2)
                                        end = min(len(lines), idx + 3)
                                        snippet = "\n".join(lines[start:end])
                                        pieces.append(ContextPiece(section=Section.CODE, content=f"{file_path}:{start+1}\n{snippet}"))
                                        break
                    except Exception as exc:  # noqa: B902
                        self.logger.warning("code_read_error", file=file_path, error=str(exc))
        except Exception as exc:
            self.logger.error("code_search_failed", error=str(exc))
        return pieces

    async def _search_qdrant(self, collection: str, keywords: List[str], limit: int = 5) -> List[str]:
        """Search a Qdrant collection for relevant payload based on keywords."""
        results: List[str] = []
        try:
            # Without embeddings, perform a scroll and simple keyword filter
            offset = None
            fetched = 0
            while fetched < limit:
                res, offset = await self.qdrant.scroll(collection, limit=32, offset=offset)
                for point in res:
                    payload = point.payload or {}
                    content = " ".join(str(v) for v in payload.values())
                    if all(kw.lower() in content.lower() for kw in keywords):
                        results.append(content)
                        fetched += 1
                        if fetched >= limit:
                            break
                if offset is None:
                    break
        except Exception as exc:  # noqa: B902
            self.logger.warning("qdrant_search_failed", collection=collection, error=str(exc))
        return results

    async def _gather_patterns(self, keywords: List[str]) -> List[ContextPiece]:
        contents = await self._search_qdrant("proven_patterns", keywords, limit=3)
        return [ContextPiece(section=Section.PATTERNS, content=c) for c in contents]

    async def _gather_anti_patterns(self, keywords: List[str]) -> List[ContextPiece]:
        contents = await self._search_qdrant("anti_patterns", keywords, limit=2)
        return [ContextPiece(section=Section.ANTI_PATTERNS, content=c) for c in contents]

    async def _gather_tools(self, keywords: List[str]) -> List[ContextPiece]:
        contents = await self._search_qdrant("tool_descriptions", keywords, limit=3)
        return [ContextPiece(section=Section.TOOLS, content=c) for c in contents]

    async def _gather_errors(self, keywords: List[str]) -> List[ContextPiece]:
        # Placeholder for error history; in a real system, fetch from logs or Qdrant
        return []


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    """Initialize the FastAPI application with routes and middleware."""
    qdrant_host = os.getenv("QDRANT_HOST", "omni-qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    code_root = os.getenv("CODE_ROOT", ".")
    service = ContextCompilerService(qdrant_host, qdrant_port, code_root)
    app = FastAPI(title="Context Compiler", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.post("/api/v1/compile", response_model=ContextResponse)
    async def compile_context_endpoint(request: ContextRequest) -> ContextResponse:
        return await service.compile_context(request.task_description, request.max_tokens)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        # Check Qdrant connectivity
        try:
            await service.qdrant.get_collections()
        except Exception:
            raise HTTPException(status_code=503, detail="Qdrant unavailable")
        return {"status": "ready"}

    return app


app = create_app()