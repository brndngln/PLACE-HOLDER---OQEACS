"""Pattern Graph SDK — typed client for the Neo4j GraphRAG Pattern API.

Usage:
    client = PatternGraphClient()
    patterns = await client.recommend_patterns("Build a REST API with caching", language="python")
    detail = await client.get_pattern("repository")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential


class PatternSummary(BaseModel):
    """Summarized pattern from recommendation results."""
    name: str
    description: str
    intent: str
    complexity: str = ""
    frequency: str = ""
    confidence: float = 0.0
    category: str = ""


class PatternDetail(BaseModel):
    """Full pattern detail with all relationships."""
    name: str
    description: str
    intent: str
    when_to_use: str = ""
    when_not_to_use: str = ""
    complexity: str = ""
    frequency: str = ""
    category: str = ""
    implementations: List[Dict[str, Any]] = Field(default_factory=list)
    related_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    principles: List[Dict[str, Any]] = Field(default_factory=list)
    trade_offs: List[Dict[str, Any]] = Field(default_factory=list)
    anti_patterns: List[Dict[str, Any]] = Field(default_factory=list)


class PatternRecommendation(BaseModel):
    """Recommendation result with ranked patterns."""
    task_description: str
    language: Optional[str] = None
    patterns: List[PatternSummary] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)


class RelatedPattern(BaseModel):
    """A related pattern with relationship context."""
    name: str
    relationship_type: str
    description: str = ""


class ImplementationDetail(BaseModel):
    """Language-specific implementation."""
    pattern_name: str
    language: str
    code_template: str = ""
    notes: str = ""
    idioms: str = ""
    caveats: str = ""


class AntiPatternResult(BaseModel):
    """Anti-pattern match result."""
    name: str
    description: str
    why_bad: str
    better_alternative: str
    related_pattern: str = ""


class PatternGraphClient:
    """Typed async client for the Neo4j GraphRAG Pattern API."""

    def __init__(self, base_url: str = "http://localhost:7475") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> PatternGraphClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def recommend_patterns(
        self,
        task_description: str,
        language: Optional[str] = None,
        limit: int = 5,
    ) -> PatternRecommendation:
        """Get pattern recommendations for a task description.

        Args:
            task_description: Natural language description of the task.
            language: Optional programming language filter.
            limit: Maximum number of patterns to return.

        Returns:
            PatternRecommendation with ranked patterns and warnings.
        """
        params: Dict[str, Any] = {"task": task_description, "limit": limit}
        if language:
            params["language"] = language
        resp = await self._client.get("/patterns/recommend", params=params)
        resp.raise_for_status()
        return PatternRecommendation(**resp.json())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_pattern(self, name: str) -> PatternDetail:
        """Get full pattern detail with implementations, relationships, principles, trade-offs.

        Args:
            name: Pattern name (e.g., 'singleton', 'repository').

        Returns:
            PatternDetail with all related data.
        """
        resp = await self._client.get(f"/patterns/{name}")
        resp.raise_for_status()
        return PatternDetail(**resp.json())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_related(self, name: str) -> List[RelatedPattern]:
        """Get related patterns (complementary, alternative, prerequisite).

        Args:
            name: Pattern name.

        Returns:
            List of RelatedPattern objects with relationship context.
        """
        resp = await self._client.get(f"/patterns/{name}/related")
        resp.raise_for_status()
        return [RelatedPattern(**item) for item in resp.json()]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_implementation(self, name: str, language: str) -> ImplementationDetail:
        """Get language-specific implementation with idioms and caveats.

        Args:
            name: Pattern name.
            language: Programming language (e.g., 'python', 'go').

        Returns:
            ImplementationDetail with code template and notes.
        """
        resp = await self._client.get(f"/patterns/{name}/implementations/{language}")
        resp.raise_for_status()
        return ImplementationDetail(**resp.json())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def find_anti_patterns(self, code_description: str) -> List[AntiPatternResult]:
        """Find anti-patterns matching a code description.

        Args:
            code_description: Description of code to analyze.

        Returns:
            List of AntiPatternResult with alternatives.
        """
        resp = await self._client.get(
            "/patterns/anti-patterns",
            params={"code_description": code_description},
        )
        resp.raise_for_status()
        return [AntiPatternResult(**item) for item in resp.json()]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def patterns_for_principle(self, principle: str) -> List[PatternSummary]:
        """Get patterns supporting a SOLID/design principle.

        Args:
            principle: Principle name (e.g., 'SRP', 'OCP', 'DIP').

        Returns:
            List of PatternSummary objects.
        """
        resp = await self._client.get(f"/patterns/for-principle/{principle}")
        resp.raise_for_status()
        return [PatternSummary(**item) for item in resp.json()]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def pattern_path(self, from_pattern: str, to_pattern: str) -> Dict[str, Any]:
        """Find shortest path between two patterns through relationships.

        Args:
            from_pattern: Starting pattern name.
            to_pattern: Target pattern name.

        Returns:
            Dict with path nodes and relationships.
        """
        resp = await self._client.post(
            "/patterns/path",
            params={"from": from_pattern, "to": to_pattern},
        )
        resp.raise_for_status()
        return resp.json()
