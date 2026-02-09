"""Neo4j Pattern Graph SDK — typed async client for the Pattern Query API v2.

Usage:
    async with Neo4jPatternClient() as client:
        rec = await client.recommend_patterns("Build a REST API with caching", language="python")
        detail = await client.get_pattern("repository")
        stats = await client.graph_stats()
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class PatternSummary(BaseModel):
    """Summarized pattern from recommendation or listing."""
    name: str
    description: str
    category: str = ""
    complexity: str = ""
    confidence: float = 0.0


class PatternRecommendation(BaseModel):
    """Recommendation result with ranked patterns."""
    task_description: str
    language: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    patterns: List[PatternSummary] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PatternDetail(BaseModel):
    """Full pattern detail with all relationships."""
    name: str
    description: str
    category: str = ""
    complexity: str = ""
    when_to_use: str = ""
    when_not_to_use: str = ""
    trade_offs: str = ""
    implementation_notes: str = ""
    related_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    anti_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    code_templates: Dict[str, str] = Field(default_factory=dict)


class PatternListItem(BaseModel):
    """Pattern from listing endpoint."""
    name: str
    description: str
    category: str = ""
    complexity: str = ""


class ExampleResult(BaseModel):
    """Real-world codebase example for a pattern."""
    pattern_name: str
    codebase: str
    component: str = ""
    file_path: str = ""
    description: str = ""


class AntiPatternResult(BaseModel):
    """Anti-pattern with fix information."""
    name: str
    description: str
    severity: str = ""
    fixed_by: str = ""


class GraphStats(BaseModel):
    """Graph node and relationship counts."""
    patterns: int = 0
    categories: int = 0
    languages: int = 0
    codebases: int = 0
    anti_patterns: int = 0
    relationships: int = 0
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class Neo4jPatternClient:
    """Typed async client for the Neo4j GraphRAG Pattern Query API v2."""

    def __init__(self, base_url: str = "http://localhost:7475") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> Neo4jPatternClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── Recommend ──────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def recommend_patterns(
        self,
        task_description: str,
        language: Optional[str] = None,
        limit: int = 5,
    ) -> PatternRecommendation:
        """Get pattern recommendations for a task description via LiteLLM extraction.

        Args:
            task_description: Natural language description of the task.
            language: Optional programming language filter.
            limit: Maximum number of patterns to return.

        Returns:
            PatternRecommendation with ranked patterns, keywords, and warnings.
        """
        payload: Dict[str, Any] = {"task": task_description, "limit": limit}
        if language:
            payload["language"] = language
        resp = await self._client.post("/patterns/recommend", json=payload)
        resp.raise_for_status()
        return PatternRecommendation(**resp.json())

    # ── List ───────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def list_patterns(
        self,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[PatternListItem]:
        """List all patterns, optionally filtered by category.

        Args:
            category: Optional category name to filter by.
            limit: Maximum patterns to return.

        Returns:
            List of PatternListItem objects.
        """
        params: Dict[str, Any] = {"limit": limit}
        if category:
            params["category"] = category
        resp = await self._client.get("/patterns", params=params)
        resp.raise_for_status()
        return [PatternListItem(**item) for item in resp.json()]

    # ── Detail ─────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_pattern(self, name: str) -> PatternDetail:
        """Get full pattern detail with relationships, anti-patterns, and code templates.

        Args:
            name: Pattern name (e.g., 'singleton', 'repository').

        Returns:
            PatternDetail with all related data.
        """
        resp = await self._client.get(f"/patterns/{name}")
        resp.raise_for_status()
        return PatternDetail(**resp.json())

    # ── Examples ───────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_examples(self, name: str) -> List[ExampleResult]:
        """Get real-world codebase examples for a pattern.

        Args:
            name: Pattern name.

        Returns:
            List of ExampleResult with codebase details.
        """
        resp = await self._client.get(f"/patterns/{name}/examples")
        resp.raise_for_status()
        return [ExampleResult(**item) for item in resp.json()]

    # ── Anti-patterns ──────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def list_antipatterns(self) -> List[AntiPatternResult]:
        """List all known anti-patterns.

        Returns:
            List of AntiPatternResult with severity and fix info.
        """
        resp = await self._client.get("/antipatterns")
        resp.raise_for_status()
        return [AntiPatternResult(**item) for item in resp.json()]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def antipatterns_for_task(self, task: str) -> List[AntiPatternResult]:
        """Find anti-patterns relevant to a task description.

        Args:
            task: Task or code description to analyze.

        Returns:
            List of matching AntiPatternResult objects.
        """
        resp = await self._client.get("/antipatterns/for-task", params={"task": task})
        resp.raise_for_status()
        return [AntiPatternResult(**item) for item in resp.json()]

    # ── Graph stats ────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def graph_stats(self) -> GraphStats:
        """Return counts of all node and relationship types.

        Returns:
            GraphStats with pattern, category, language, codebase counts.
        """
        resp = await self._client.get("/graph/stats")
        resp.raise_for_status()
        return GraphStats(**resp.json())

    # ── Health ─────────────────────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Check API liveness."""
        resp = await self._client.get("/health")
        resp.raise_for_status()
        return resp.json()

    async def ready(self) -> Dict[str, Any]:
        """Check API readiness (Neo4j connectivity)."""
        resp = await self._client.get("/ready")
        resp.raise_for_status()
        return resp.json()
