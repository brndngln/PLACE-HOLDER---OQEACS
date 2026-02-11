"""Qdrant search wrapper for semantic retrieval."""
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import ScoredPoint
import structlog

logger = structlog.get_logger()


class QdrantSearchService:
    """Wraps Qdrant operations for context retrieval."""

    def __init__(self, qdrant_url: str) -> None:
        self.client = AsyncQdrantClient(url=qdrant_url)

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 20,
        score_threshold: float = 0.7,
    ) -> list[ScoredPoint]:
        """Semantic search against a Qdrant collection."""
        try:
            results = await self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )
            logger.info(
                "qdrant_search",
                collection=collection_name,
                results=len(results),
                threshold=score_threshold,
            )
            return results
        except Exception as exc:
            logger.warning("qdrant_search_failed", collection=collection_name, error=str(exc))
            return []

    async def set_payload(
        self,
        collection_name: str,
        payload: dict,
        points: list[str | int],
    ) -> None:
        """Update payload on existing points."""
        try:
            await self.client.set_payload(
                collection_name=collection_name,
                payload=payload,
                points=points,
            )
        except Exception as exc:
            logger.warning("qdrant_set_payload_failed", error=str(exc))

    async def upsert_point(
        self,
        collection_name: str,
        point_id: str,
        vector: list[float],
        payload: dict,
    ) -> None:
        """Insert or update a single point."""
        from qdrant_client.models import PointStruct

        try:
            await self.client.upsert(
                collection_name=collection_name,
                points=[PointStruct(id=point_id, vector=vector, payload=payload)],
            )
        except Exception as exc:
            logger.warning("qdrant_upsert_failed", error=str(exc))

    async def close(self) -> None:
        """Close the Qdrant client."""
        await self.client.close()
