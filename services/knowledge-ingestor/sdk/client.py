"""Knowledge Ingestor SDK — typed client for the Knowledge Ingestor API.

Usage:
    client = KnowledgeIngestorClient()
    result = await client.ingest_repository(
        source_url="https://github.com/redis/redis.git",
        source_name="redis",
        languages=["c"],
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential


class IngestionResult(BaseModel):
    """Result from an ingestion operation."""
    job_id: str
    source_name: str
    status: str
    files_processed: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    started_at: str = ""
    completed_at: Optional[str] = None


class KnowledgeIngestorClient:
    """Typed async client for the Knowledge Ingestor service."""

    def __init__(self, base_url: str = "http://localhost:9420") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> KnowledgeIngestorClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def ingest_repository(
        self,
        source_url: str,
        source_name: str,
        languages: List[str],
        source_category: str = "general",
        branch: str = "main",
        file_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        collection: str = "elite_codebases",
        chunk_strategy: str = "ast",
        max_files: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> IngestionResult:
        """Ingest a Git repository.

        Args:
            source_url: Git clone URL.
            source_name: Unique name for this source.
            languages: List of programming languages to parse.
            source_category: Category label.
            branch: Git branch to clone.
            file_patterns: Glob patterns for files to include.
            exclude_patterns: Glob patterns for files to exclude.
            collection: Target Qdrant collection.
            chunk_strategy: One of ast, file, function, class.
            max_files: Maximum files to process.
            tags: Metadata tags.

        Returns:
            IngestionResult with job details.
        """
        payload = {
            "source_url": source_url,
            "source_name": source_name,
            "source_category": source_category,
            "branch": branch,
            "languages": languages,
            "file_patterns": file_patterns or ["*.*"],
            "exclude_patterns": exclude_patterns or [],
            "collection": collection,
            "chunk_strategy": chunk_strategy,
            "max_files": max_files,
            "tags": tags or [],
        }
        resp = await self._client.post("/ingest/repository", json=payload)
        resp.raise_for_status()
        return IngestionResult(**resp.json())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def ingest_paper(
        self,
        pdf_url: str,
        title: str,
        authors: Optional[List[str]] = None,
        year: int = 2024,
        venue: str = "",
        domain: str = "computer-science",
        tags: Optional[List[str]] = None,
    ) -> IngestionResult:
        """Ingest an academic paper PDF.

        Args:
            pdf_url: URL to the PDF file.
            title: Paper title.
            authors: List of author names.
            year: Publication year.
            venue: Conference or journal name.
            domain: Knowledge domain.
            tags: Metadata tags.

        Returns:
            IngestionResult with job details.
        """
        payload = {
            "pdf_url": pdf_url,
            "title": title,
            "authors": authors or [],
            "year": year,
            "venue": venue,
            "domain": domain,
            "tags": tags or [],
        }
        resp = await self._client.post("/ingest/paper", json=payload)
        resp.raise_for_status()
        return IngestionResult(**resp.json())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def ingest_blog(
        self,
        url: str,
        source: str = "",
        domain: str = "engineering",
        tags: Optional[List[str]] = None,
    ) -> IngestionResult:
        """Ingest a technical blog post.

        Args:
            url: Blog post URL.
            source: Source name.
            domain: Knowledge domain.
            tags: Metadata tags.

        Returns:
            IngestionResult with job details.
        """
        payload = {"url": url, "source": source, "domain": domain, "tags": tags or []}
        resp = await self._client.post("/ingest/blog", json=payload)
        resp.raise_for_status()
        return IngestionResult(**resp.json())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def ingest_postmortem(
        self,
        url: str,
        source: str = "",
        tags: Optional[List[str]] = None,
    ) -> IngestionResult:
        """Ingest a post-mortem report.

        Args:
            url: Post-mortem URL.
            source: Source name.
            tags: Metadata tags.

        Returns:
            IngestionResult with job details.
        """
        payload = {"url": url, "source": source, "tags": tags or []}
        resp = await self._client.post("/ingest/postmortem", json=payload)
        resp.raise_for_status()
        return IngestionResult(**resp.json())

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def trigger_batch_ingestion(self, concurrency: int = 3) -> Dict[str, Any]:
        """Trigger batch ingestion from sources-config.yaml.

        Args:
            concurrency: Number of parallel ingestion jobs.

        Returns:
            Batch summary with completed/failed counts.
        """
        resp = await self._client.post("/ingest/batch", json={"concurrency": concurrency})
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_status(self) -> Dict[str, Any]:
        """Get current ingestion status and queue depth.

        Returns:
            Status dict with running jobs and queue depth.
        """
        resp = await self._client.get("/ingest/status")
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get ingestion history for the last N days.

        Args:
            days: Number of days of history to retrieve.

        Returns:
            List of job summaries.
        """
        resp = await self._client.get("/ingest/history", params={"days": days})
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_stats(self) -> Dict[str, Any]:
        """Get aggregated ingestion statistics.

        Returns:
            Stats dict with total docs, embeddings, collection counts.
        """
        resp = await self._client.get("/ingest/stats")
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def delete_source(self, source_name: str) -> Dict[str, str]:
        """Delete a source from Qdrant and MinIO.

        Args:
            source_name: Name of the source to delete.

        Returns:
            Deletion confirmation.
        """
        resp = await self._client.delete(f"/ingest/{source_name}")
        resp.raise_for_status()
        return resp.json()
