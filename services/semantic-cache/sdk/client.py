# sdk/client.py
# ═══════════════════════════════════════════════════════════════════════════════
# SEMANTIC CACHE SDK — OMNI QUANTUM ELITE
# System 44 — Semantic Cache
# Container: omni-semantic-cache | Port: 9440
# ═══════════════════════════════════════════════════════════════════════════════

"""
Client for the Semantic Cache service. Checks for semantically similar
cached LLM responses before routing to providers, and stores new responses
after generation. Called by Token Infinity to save cost and latency.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger("omni.quantum.semantic_cache")


class CacheCategory(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    KNOWLEDGE_QUERY = "knowledge_query"
    DOCUMENTATION = "documentation"
    SPEC_GENERATION = "spec_generation"


@dataclass
class CacheHit:
    """Represents a cache hit with the cached response."""
    hit: bool
    similarity: float
    cached_response: Optional[str] = None
    model: Optional[str] = None
    cached_at: Optional[datetime] = None
    hit_count: int = 0
    category: Optional[CacheCategory] = None
    latency_saved_ms: Optional[float] = None
    cost_saved_usd: Optional[float] = None


@dataclass
class CacheStoreResult:
    """Result of storing a new response in the cache."""
    stored: bool
    cache_key: str
    category: CacheCategory
    ttl_seconds: int
    embedding_tokens: int


@dataclass
class CacheStats:
    """Aggregate cache statistics."""
    total_hits: int
    total_misses: int
    hit_rate: float
    entries_by_category: dict[str, int] = field(default_factory=dict)
    estimated_cost_savings_usd: float = 0.0
    estimated_latency_savings_seconds: float = 0.0
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None
    total_entries: int = 0
    cache_size_mb: float = 0.0


@dataclass
class InvalidationResult:
    """Result of a cache invalidation operation."""
    invalidated: bool
    entries_removed: int
    category: Optional[str] = None


class SemanticCacheClient:
    """
    Async client for the Omni Quantum Semantic Cache service.

    Usage:
        client = SemanticCacheClient()

        # Check cache before calling LLM
        result = await client.check("How do I implement a circuit breaker?", "code_generation")
        if result.hit:
            response = result.cached_response  # Use cached response
        else:
            response = await call_llm(...)  # Call LLM
            await client.store(prompt, response, "code_generation", model="devstral-2:123b")

        # Get cache statistics
        stats = await client.get_stats()
        print(f"Hit rate: {stats.hit_rate:.1%}, savings: ${stats.estimated_cost_savings_usd:.2f}")
    """

    def __init__(
        self,
        base_url: str = "http://omni-semantic-cache:9440",
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def check(
        self,
        prompt: str,
        category: str = "code_generation",
        similarity_threshold: Optional[float] = None,
    ) -> CacheHit:
        """
        Check if a semantically similar prompt has a cached response.

        Args:
            prompt: The prompt text to check against cache.
            category: Cache category for scoped lookup.
            similarity_threshold: Override default 0.95 threshold.

        Returns:
            CacheHit with hit=True and cached_response if found,
            or hit=False if no sufficiently similar entry exists.
        """
        client = await self._get_client()
        payload: dict[str, Any] = {
            "prompt": prompt,
            "category": category,
        }
        if similarity_threshold is not None:
            payload["similarity_threshold"] = similarity_threshold

        try:
            resp = await client.post("/cache/check", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return CacheHit(
                hit=data.get("hit", False),
                similarity=data.get("similarity", 0.0),
                cached_response=data.get("cached_response"),
                model=data.get("model"),
                cached_at=(
                    datetime.fromisoformat(data["cached_at"])
                    if data.get("cached_at")
                    else None
                ),
                hit_count=data.get("hit_count", 0),
                category=(
                    CacheCategory(data["category"])
                    if data.get("category")
                    else None
                ),
                latency_saved_ms=data.get("latency_saved_ms"),
                cost_saved_usd=data.get("cost_saved_usd"),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "Cache check failed",
                status=e.response.status_code,
                detail=e.response.text,
            )
            # On cache failure, return miss — never block the pipeline
            return CacheHit(hit=False, similarity=0.0)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Cache service unreachable, treating as miss", error=str(e))
            return CacheHit(hit=False, similarity=0.0)

    async def store(
        self,
        prompt: str,
        response: str,
        category: str = "code_generation",
        model: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> CacheStoreResult:
        """
        Store a new LLM response in the cache.

        Args:
            prompt: The original prompt.
            response: The LLM response to cache.
            category: Cache category (determines TTL).
            model: Model that generated the response.
            metadata: Optional metadata (task_id, trace_id, etc.).

        Returns:
            CacheStoreResult with storage confirmation and TTL.
        """
        client = await self._get_client()
        payload: dict[str, Any] = {
            "prompt": prompt,
            "response": response,
            "category": category,
        }
        if model:
            payload["model"] = model
        if metadata:
            payload["metadata"] = metadata

        try:
            resp = await client.post("/cache/store", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return CacheStoreResult(
                stored=data.get("stored", False),
                cache_key=data.get("cache_key", ""),
                category=CacheCategory(data.get("category", category)),
                ttl_seconds=data.get("ttl_seconds", 0),
                embedding_tokens=data.get("embedding_tokens", 0),
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "Cache store failed",
                status=e.response.status_code,
                detail=e.response.text,
            )
            return CacheStoreResult(
                stored=False,
                cache_key="",
                category=CacheCategory(category),
                ttl_seconds=0,
                embedding_tokens=0,
            )
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Cache service unreachable, skipping store", error=str(e))
            return CacheStoreResult(
                stored=False,
                cache_key="",
                category=CacheCategory(category),
                ttl_seconds=0,
                embedding_tokens=0,
            )

    async def invalidate(
        self,
        category: Optional[str] = None,
    ) -> InvalidationResult:
        """
        Invalidate cache entries by category, or all entries if no category specified.

        Args:
            category: Specific category to invalidate, or None for all.

        Returns:
            InvalidationResult with count of removed entries.
        """
        client = await self._get_client()

        try:
            if category:
                resp = await client.delete(f"/cache/invalidate/{category}")
            else:
                resp = await client.delete("/cache/invalidate/all")
            resp.raise_for_status()
            data = resp.json()
            return InvalidationResult(
                invalidated=data.get("invalidated", False),
                entries_removed=data.get("entries_removed", 0),
                category=category,
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "Cache invalidation failed",
                status=e.response.status_code,
                detail=e.response.text,
            )
            return InvalidationResult(invalidated=False, entries_removed=0, category=category)

    async def get_stats(self) -> CacheStats:
        """
        Get cache statistics including hit rate, entry counts, and estimated savings.

        Returns:
            CacheStats with comprehensive cache metrics.
        """
        client = await self._get_client()

        try:
            resp = await client.get("/cache/stats")
            resp.raise_for_status()
            data = resp.json()
            return CacheStats(
                total_hits=data.get("total_hits", 0),
                total_misses=data.get("total_misses", 0),
                hit_rate=data.get("hit_rate", 0.0),
                entries_by_category=data.get("entries_by_category", {}),
                estimated_cost_savings_usd=data.get("estimated_cost_savings_usd", 0.0),
                estimated_latency_savings_seconds=data.get(
                    "estimated_latency_savings_seconds", 0.0
                ),
                oldest_entry=(
                    datetime.fromisoformat(data["oldest_entry"])
                    if data.get("oldest_entry")
                    else None
                ),
                newest_entry=(
                    datetime.fromisoformat(data["newest_entry"])
                    if data.get("newest_entry")
                    else None
                ),
                total_entries=data.get("total_entries", 0),
                cache_size_mb=data.get("cache_size_mb", 0.0),
            )
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
            logger.error("Failed to get cache stats", error=str(e))
            return CacheStats(
                total_hits=0,
                total_misses=0,
                hit_rate=0.0,
                total_entries=0,
            )

    async def health(self) -> dict[str, Any]:
        """Check cache service health."""
        client = await self._get_client()
        try:
            resp = await client.get("/health")
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException):
            return {"status": "unreachable"}

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "SemanticCacheClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
