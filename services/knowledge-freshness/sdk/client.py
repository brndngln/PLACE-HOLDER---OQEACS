"""Knowledge Freshness Monitor SDK — typed client for the Freshness API.

Usage:
    client = FreshnessClient()
    stale = await client.get_stale_sources()
    await client.trigger_reingest("postgresql")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential


class SourceFreshness(BaseModel):
    """Freshness data for a single source."""
    source_name: str
    tier: str = "tier-2"
    freshness_score: int
    last_ingested: Optional[str] = None
    last_source_updated: Optional[str] = None
    latest_release: Optional[str] = None
    latest_commit: Optional[str] = None
    needs_reingestion: bool = False
    collection: str = "elite_codebases"
    source_url: str = ""


class FeedStatus(BaseModel):
    """Status of an RSS feed watcher."""
    feed_name: str
    rss_url: str
    last_checked: Optional[str] = None
    new_posts_found: int = 0
    last_error: Optional[str] = None


class SecurityAdvisory(BaseModel):
    """A security advisory."""
    cve_id: str
    description: str
    severity: str
    affected_source: str
    published: str
    url: str


class FreshnessClient:
    """Typed async client for the Knowledge Freshness Monitor service."""

    def __init__(self, base_url: str = "http://localhost:9430") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> FreshnessClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_all_freshness(self) -> List[SourceFreshness]:
        """Get all sources sorted by staleness.

        Returns:
            List of SourceFreshness sorted by freshness_score ascending.
        """
        resp = await self._client.get("/freshness")
        resp.raise_for_status()
        return [SourceFreshness(**item) for item in resp.json()]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_source_freshness(self, name: str) -> SourceFreshness:
        """Get detailed freshness info for a specific source.

        Args:
            name: Source name.

        Returns:
            SourceFreshness with full details.
        """
        resp = await self._client.get(f"/freshness/{name}")
        resp.raise_for_status()
        return SourceFreshness(**resp.json())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_stale_sources(self) -> List[SourceFreshness]:
        """Get sources with freshness score <50.

        Returns:
            List of stale SourceFreshness objects.
        """
        resp = await self._client.get("/freshness/stale")
        resp.raise_for_status()
        return [SourceFreshness(**item) for item in resp.json()]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def trigger_check(self) -> Dict[str, str]:
        """Trigger an immediate full freshness check.

        Returns:
            Status confirmation.
        """
        resp = await self._client.post("/freshness/check-now")
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def trigger_reingest(self, source_name: str) -> Dict[str, str]:
        """Manually trigger re-ingestion for a source.

        Args:
            source_name: Name of the source to re-ingest.

        Returns:
            Queuing confirmation.
        """
        resp = await self._client.post(f"/freshness/reingest/{source_name}")
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_feed_status(self) -> List[FeedStatus]:
        """Get RSS feed monitoring status.

        Returns:
            List of FeedStatus objects.
        """
        resp = await self._client.get("/feeds/status")
        resp.raise_for_status()
        return [FeedStatus(**item) for item in resp.json()]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_advisories(self) -> List[SecurityAdvisory]:
        """Get security advisories affecting the stack.

        Returns:
            List of SecurityAdvisory objects.
        """
        resp = await self._client.get("/advisories")
        resp.raise_for_status()
        return [SecurityAdvisory(**item) for item in resp.json()]
