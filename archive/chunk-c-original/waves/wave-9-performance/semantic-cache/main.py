# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  LLM SEMANTIC CACHE — 20-40% Cost Reduction via Embedding Similarity               ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝

import asyncio
import hashlib
import json
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
import asyncpg
import numpy as np
import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

QDRANT_URL = os.getenv("QDRANT_URL", "http://omni-qdrant:6333")
LITELLM_URL = os.getenv("LITELLM_URL", "http://omni-litellm:4000")
REDIS_URL = os.getenv("REDIS_URL", "redis://omni-redis:6379")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://fortress:quantum_elite_2024@omni-postgres:5432/financial_fortress")

CACHE_COLLECTION = "semantic_cache"
SIMILARITY_THRESHOLD = 0.95
MAX_CACHE_ENTRIES = 10000
CACHE_TTL_SECONDS = 3600
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = "gpt-4"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False

class CacheStats(BaseModel):
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    tokens_saved: int
    estimated_cost_saved_usd: float
    avg_latency_saved_ms: float

# ─────────────────────────────────────────────────────────────────────────────
# Semantic Cache Service
# ─────────────────────────────────────────────────────────────────────────────

class SemanticCacheService:
    def __init__(self):
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "tokens_saved": 0,
            "latency_saved_ms": 0,
        }
        self._http: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        await self._ensure_collection()
        logger.info("semantic_cache_initialized", collection=CACHE_COLLECTION)

    async def shutdown(self):
        if self._http:
            await self._http.close()

    async def _ensure_collection(self):
        """Create Qdrant collection if it doesn't exist."""
        try:
            async with self._http.get(f"{QDRANT_URL}/collections/{CACHE_COLLECTION}") as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass

        payload = {
            "vectors": {"size": EMBEDDING_DIM, "distance": "Cosine"},
            "optimizers_config": {"indexing_threshold": 1000},
        }
        async with self._http.put(
            f"{QDRANT_URL}/collections/{CACHE_COLLECTION}",
            json=payload
        ) as resp:
            if resp.status not in (200, 201):
                logger.warning("qdrant_collection_create_failed", status=resp.status)

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding from LiteLLM."""
        payload = {"model": EMBEDDING_MODEL, "input": text}
        async with self._http.post(f"{LITELLM_URL}/embeddings", json=payload) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=502, detail="Embedding service unavailable")
            data = await resp.json()
            return data["data"][0]["embedding"]

    async def _search_similar(self, embedding: List[float]) -> Optional[Dict]:
        """Search Qdrant for similar cached prompts."""
        payload = {
            "vector": embedding,
            "limit": 1,
            "score_threshold": SIMILARITY_THRESHOLD,
            "with_payload": True,
        }
        async with self._http.post(
            f"{QDRANT_URL}/collections/{CACHE_COLLECTION}/points/search",
            json=payload
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            results = data.get("result", [])
            if results and results[0].get("score", 0) >= SIMILARITY_THRESHOLD:
                return results[0].get("payload")
        return None

    async def _store_in_cache(self, prompt_hash: str, embedding: List[float], 
                              prompt: str, response: Dict, tokens_used: int):
        """Store prompt/response in Qdrant cache."""
        point_id = int(hashlib.md5(prompt_hash.encode()).hexdigest()[:16], 16) % (2**63)
        payload = {
            "points": [{
                "id": point_id,
                "vector": embedding,
                "payload": {
                    "prompt_hash": prompt_hash,
                    "prompt": prompt[:1000],
                    "response": response,
                    "tokens_used": tokens_used,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "hit_count": 0,
                }
            }]
        }
        async with self._http.put(
            f"{QDRANT_URL}/collections/{CACHE_COLLECTION}/points",
            json=payload
        ) as resp:
            if resp.status not in (200, 201):
                logger.warning("cache_store_failed", status=resp.status)

    def _build_prompt_key(self, messages: List[ChatMessage]) -> str:
        """Build a deterministic key from messages."""
        content = "|".join(f"{m.role}:{m.content}" for m in messages)
        return hashlib.sha256(content.encode()).hexdigest()

    async def chat_completion(self, request: ChatRequest) -> Dict[str, Any]:
        """Main entry point: check cache, forward to LLM if miss, cache response."""
        start_time = time.time()
        self.stats["total_requests"] += 1

        # Build prompt text for embedding
        prompt_text = "\n".join(f"{m.role}: {m.content}" for m in request.messages)
        prompt_hash = self._build_prompt_key(request.messages)

        # Get embedding
        try:
            embedding = await self._get_embedding(prompt_text)
        except Exception as e:
            logger.error("embedding_failed", error=str(e))
            # Fall through to LLM without cache
            return await self._forward_to_llm(request)

        # Search cache
        cached = await self._search_similar(embedding)
        if cached:
            self.stats["cache_hits"] += 1
            tokens_saved = cached.get("tokens_used", 0)
            self.stats["tokens_saved"] += tokens_saved
            latency_saved = (time.time() - start_time) * 1000
            self.stats["latency_saved_ms"] += latency_saved

            logger.info("cache_hit", 
                        prompt_hash=prompt_hash[:12], 
                        tokens_saved=tokens_saved,
                        latency_saved_ms=round(latency_saved, 2))

            response = cached.get("response", {})
            response["_cache"] = {"hit": True, "tokens_saved": tokens_saved}
            return response

        # Cache miss — forward to LLM
        self.stats["cache_misses"] += 1
        response = await self._forward_to_llm(request)

        # Store in cache
        tokens_used = response.get("usage", {}).get("total_tokens", 0)
        await self._store_in_cache(prompt_hash, embedding, prompt_text, response, tokens_used)

        response["_cache"] = {"hit": False}
        logger.info("cache_miss", prompt_hash=prompt_hash[:12], tokens_used=tokens_used)
        return response

    async def _forward_to_llm(self, request: ChatRequest) -> Dict[str, Any]:
        """Forward request to LiteLLM."""
        payload = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        async with self._http.post(f"{LITELLM_URL}/chat/completions", json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise HTTPException(status_code=resp.status, detail=f"LLM error: {text[:200]}")
            return await resp.json()

    async def flush_cache(self) -> Dict[str, str]:
        """Delete all cached entries."""
        async with self._http.delete(f"{QDRANT_URL}/collections/{CACHE_COLLECTION}") as resp:
            pass
        await self._ensure_collection()
        return {"status": "cache_flushed"}

    def get_stats(self) -> CacheStats:
        total = self.stats["total_requests"]
        hits = self.stats["cache_hits"]
        hit_rate = (hits / total * 100) if total > 0 else 0
        tokens = self.stats["tokens_saved"]
        # Rough estimate: $0.002 per 1K tokens for GPT-4
        cost_saved = (tokens / 1000) * 0.002
        avg_latency = (self.stats["latency_saved_ms"] / hits) if hits > 0 else 0

        return CacheStats(
            total_requests=total,
            cache_hits=hits,
            cache_misses=self.stats["cache_misses"],
            hit_rate=round(hit_rate, 2),
            tokens_saved=tokens,
            estimated_cost_saved_usd=round(cost_saved, 4),
            avg_latency_saved_ms=round(avg_latency, 2),
        )

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────────────────────

cache_service = SemanticCacheService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache_service.initialize()
    logger.info("semantic_cache_started", port=8380)
    yield
    await cache_service.shutdown()

app = FastAPI(
    title="LLM Semantic Cache",
    description="20-40% cost reduction via embedding similarity caching",
    version="3.0.0",
    lifespan=lifespan,
)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "semantic-cache", "version": "3.0.0"}

@app.get("/ready")
async def ready():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{QDRANT_URL}/collections") as resp:
                if resp.status == 200:
                    return {"status": "ready"}
        raise HTTPException(status_code=503, detail="Qdrant not ready")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/api/v1/chat")
async def chat_completion(request: ChatRequest):
    """Main chat endpoint with semantic caching."""
    return await cache_service.chat_completion(request)

@app.get("/api/v1/cache/stats")
async def get_cache_stats():
    """Get cache performance statistics."""
    return cache_service.get_stats()

@app.delete("/api/v1/cache")
async def flush_cache():
    """Flush all cached entries."""
    return await cache_service.flush_cache()

@app.get("/metrics")
async def metrics():
    stats = cache_service.get_stats()
    return {
        "cache_requests_total": stats.total_requests,
        "cache_hits_total": stats.cache_hits,
        "cache_misses_total": stats.cache_misses,
        "cache_hit_rate": stats.hit_rate,
        "tokens_saved_total": stats.tokens_saved,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8380")))
