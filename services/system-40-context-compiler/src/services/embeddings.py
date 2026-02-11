"""Embedding helper — calls LiteLLM for vector embeddings."""
import httpx
import structlog

logger = structlog.get_logger()


class EmbeddingService:
    """Generate embeddings via LiteLLM (OpenAI-compatible API)."""

    def __init__(self, litellm_url: str, model: str = "text-embedding-3-small") -> None:
        self.litellm_url = litellm_url.rstrip("/")
        self.model = model

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for a single text."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.litellm_url}/v1/embeddings",
                json={"model": self.model, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.litellm_url}/v1/embeddings",
                json={"model": self.model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
