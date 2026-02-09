"""Semantic Cache — Redis-backed embedding similarity cache for LLM responses.

Sits between Token Infinity and the LLM routing layer, caching responses by
semantic similarity of prompts. Uses Redis for persistence (survives restarts)
with category-based TTLs. Cosine similarity threshold of 0.95 by default.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
import numpy as np
import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, HTTPException
from langfuse import Langfuse
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import Response
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

REDIS_URL = os.getenv("REDIS_URL", "redis://omni-redis:6379/0")
LITELLM_URL = os.getenv("LITELLM_URL", "http://omni-litellm:4000")
LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.95"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536
MAX_CACHE_ENTRIES = int(os.getenv("MAX_CACHE_ENTRIES", "50000"))

# Category → TTL in seconds
CATEGORY_TTLS: Dict[str, int] = {
    "code_generation": 3600,       # 1 hour
    "code_review": 86400,          # 24 hours
    "knowledge_query": 604800,     # 7 days
    "documentation": 604800,       # 7 days
    "spec_generation": 14400,      # 4 hours
}
DEFAULT_TTL = 3600

# Redis key prefixes
EMBEDDING_PREFIX = "sc:emb:"
RESPONSE_PREFIX = "sc:resp:"
INDEX_KEY = "sc:index"
STATS_KEY = "sc:stats"

# ─────────────────────────────────────────────────────────────────────────────
# Prometheus Metrics
# ─────────────────────────────────────────────────────────────────────────────

CACHE_HITS = Counter(
    "cache_hits_total", "Total cache hits", ["category"]
)
CACHE_MISSES = Counter(
    "cache_misses_total", "Total cache misses", ["category"]
)
CACHE_HIT_RATE = Gauge(
    "cache_hit_rate", "Current cache hit rate"
)
CACHE_ENTRIES = Gauge(
    "cache_entries_total", "Total cache entries", ["category"]
)
CACHE_LATENCY_SAVINGS = Histogram(
    "cache_latency_savings_seconds", "Latency saved by cache hits",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)
CACHE_COST_SAVINGS = Counter(
    "cache_cost_savings_estimated", "Estimated cost savings in USD"
)
CACHE_SIMILARITY_THRESHOLD = Gauge(
    "cache_similarity_threshold", "Current similarity threshold"
)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────


class CacheCategory(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    KNOWLEDGE_QUERY = "knowledge_query"
    DOCUMENTATION = "documentation"
    SPEC_GENERATION = "spec_generation"


class CacheCheckRequest(BaseModel):
    """Request to check cache for a prompt."""
    prompt: str
    category: CacheCategory = CacheCategory.CODE_GENERATION
    model: str = "gpt-4"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CacheCheckResponse(BaseModel):
    """Response from cache check."""
    hit: bool
    cached_response: Optional[Dict[str, Any]] = None
    similarity_score: Optional[float] = None
    cache_key: Optional[str] = None
    tokens_saved: int = 0
    latency_saved_ms: float = 0.0


class CacheStoreRequest(BaseModel):
    """Request to store a new response in cache."""
    prompt: str
    response: Dict[str, Any]
    category: CacheCategory = CacheCategory.CODE_GENERATION
    model: str = "gpt-4"
    tokens_used: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CacheStatsResponse(BaseModel):
    """Cache statistics."""
    total_entries: int
    entries_per_category: Dict[str, int]
    total_hits: int
    total_misses: int
    hit_rate: float
    estimated_cost_saved_usd: float
    estimated_latency_saved_seconds: float
    similarity_threshold: float


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ─────────────────────────────────────────────────────────────────────────────
# Semantic Cache Engine
# ─────────────────────────────────────────────────────────────────────────────

class SemanticCacheEngine:
    """Redis-backed semantic similarity cache for LLM responses."""

    def __init__(self) -> None:
        self.redis: Optional[aioredis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.langfuse: Optional[Langfuse] = None
        self._total_hits: int = 0
        self._total_misses: int = 0
        self._total_cost_saved: float = 0.0
        self._total_latency_saved: float = 0.0

    async def initialize(self) -> None:
        """Initialize Redis and HTTP connections."""
        self.redis = aioredis.from_url(
            REDIS_URL,
            decode_responses=False,
            max_connections=20,
        )
        self.http_client = httpx.AsyncClient(timeout=30.0)

        if LANGFUSE_PUBLIC_KEY:
            try:
                self.langfuse = Langfuse(
                    public_key=LANGFUSE_PUBLIC_KEY,
                    secret_key=LANGFUSE_SECRET_KEY,
                    host=LANGFUSE_URL,
                )
            except Exception as e:
                logger.warning("langfuse_init_failed", error=str(e))

        # Restore stats from Redis
        await self._restore_stats()

        CACHE_SIMILARITY_THRESHOLD.set(SIMILARITY_THRESHOLD)
        logger.info("semantic_cache_initialized", threshold=SIMILARITY_THRESHOLD)

    async def shutdown(self) -> None:
        """Persist stats and close connections."""
        await self._persist_stats()
        if self.redis:
            await self.redis.aclose()
        if self.http_client:
            await self.http_client.aclose()
        if self.langfuse:
            try:
                self.langfuse.flush()
            except Exception:
                pass

    async def _restore_stats(self) -> None:
        """Restore accumulated stats from Redis."""
        try:
            raw = await self.redis.get(STATS_KEY)
            if raw:
                stats = json.loads(raw)
                self._total_hits = stats.get("total_hits", 0)
                self._total_misses = stats.get("total_misses", 0)
                self._total_cost_saved = stats.get("total_cost_saved", 0.0)
                self._total_latency_saved = stats.get("total_latency_saved", 0.0)
        except Exception:
            pass

    async def _persist_stats(self) -> None:
        """Persist stats to Redis."""
        try:
            stats = {
                "total_hits": self._total_hits,
                "total_misses": self._total_misses,
                "total_cost_saved": self._total_cost_saved,
                "total_latency_saved": self._total_latency_saved,
            }
            await self.redis.set(STATS_KEY, json.dumps(stats))
        except Exception:
            pass

    # ── Embedding generation ──────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=0.5, max=5))
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding via LiteLLM."""
        truncated = " ".join(text.split()[:8000])
        resp = await self.http_client.post(
            f"{LITELLM_URL}/embeddings",
            json={"model": EMBEDDING_MODEL, "input": truncated},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    # ── Cosine similarity ─────────────────────────────────────────────────

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a_arr = np.array(a, dtype=np.float32)
        b_arr = np.array(b, dtype=np.float32)
        dot = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    # ── Cache key generation ──────────────────────────────────────────────

    @staticmethod
    def _prompt_hash(prompt: str) -> str:
        """Generate a deterministic hash for a prompt."""
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:32]

    # ── Core cache operations ─────────────────────────────────────────────

    async def check(self, req: CacheCheckRequest) -> CacheCheckResponse:
        """Check cache for a semantically similar prompt.

        1. Generate embedding of the prompt
        2. Scan Redis for cached embeddings in the same category
        3. If cosine similarity > threshold, return cached response
        4. Otherwise return miss
        """
        start_time = time.time()
        category = req.category.value

        try:
            query_embedding = await self._generate_embedding(req.prompt)
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            self._total_misses += 1
            CACHE_MISSES.labels(category=category).inc()
            return CacheCheckResponse(hit=False)

        # Scan all cached embeddings for this category
        pattern = f"{EMBEDDING_PREFIX}{category}:*"
        best_score = 0.0
        best_key = None

        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
                for key in keys:
                    raw_emb = await self.redis.get(key)
                    if not raw_emb:
                        continue
                    cached_embedding = json.loads(raw_emb)
                    score = self._cosine_similarity(query_embedding, cached_embedding)
                    if score > best_score:
                        best_score = score
                        best_key = key

                if cursor == 0:
                    break

        except Exception as e:
            logger.error("cache_scan_failed", error=str(e))
            self._total_misses += 1
            CACHE_MISSES.labels(category=category).inc()
            return CacheCheckResponse(hit=False)

        # Check if best match exceeds threshold
        if best_score >= SIMILARITY_THRESHOLD and best_key:
            # Extract the prompt hash from the key
            key_str = best_key.decode("utf-8") if isinstance(best_key, bytes) else best_key
            prompt_hash = key_str.split(":")[-1]
            response_key = f"{RESPONSE_PREFIX}{category}:{prompt_hash}"

            raw_resp = await self.redis.get(response_key)
            if raw_resp:
                cached_data = json.loads(raw_resp)
                tokens_saved = cached_data.get("tokens_used", 0)
                latency_saved_ms = (time.time() - start_time) * 1000

                # Update stats
                self._total_hits += 1
                cost_saved = (tokens_saved / 1000) * 0.002
                self._total_cost_saved += cost_saved
                self._total_latency_saved += latency_saved_ms / 1000

                CACHE_HITS.labels(category=category).inc()
                CACHE_LATENCY_SAVINGS.observe(latency_saved_ms / 1000)
                CACHE_COST_SAVINGS.inc(cost_saved)
                self._update_hit_rate()

                # Increment hit count
                cached_data["hit_count"] = cached_data.get("hit_count", 0) + 1
                await self.redis.set(response_key, json.dumps(cached_data))

                # Langfuse trace
                if self.langfuse:
                    try:
                        self.langfuse.trace(
                            name="cache_hit",
                            input={"prompt": req.prompt[:200], "category": category},
                            output={"similarity": best_score, "tokens_saved": tokens_saved},
                        )
                    except Exception:
                        pass

                logger.info(
                    "cache_hit",
                    category=category,
                    similarity=round(best_score, 4),
                    tokens_saved=tokens_saved,
                )

                return CacheCheckResponse(
                    hit=True,
                    cached_response=cached_data.get("response"),
                    similarity_score=round(best_score, 4),
                    cache_key=prompt_hash,
                    tokens_saved=tokens_saved,
                    latency_saved_ms=round(latency_saved_ms, 2),
                )

        # Cache miss
        self._total_misses += 1
        CACHE_MISSES.labels(category=category).inc()
        self._update_hit_rate()

        logger.info("cache_miss", category=category, best_similarity=round(best_score, 4))

        return CacheCheckResponse(hit=False, similarity_score=round(best_score, 4) if best_score > 0 else None)

    async def store(self, req: CacheStoreRequest) -> Dict[str, str]:
        """Store a new prompt/response pair in the cache.

        Stores the embedding and response in Redis with category-based TTL.
        """
        category = req.category.value
        prompt_hash = self._prompt_hash(req.prompt)
        ttl = CATEGORY_TTLS.get(category, DEFAULT_TTL)

        try:
            embedding = await self._generate_embedding(req.prompt)
        except Exception as e:
            logger.error("store_embedding_failed", error=str(e))
            raise HTTPException(status_code=502, detail="Embedding generation failed")

        # Store embedding
        emb_key = f"{EMBEDDING_PREFIX}{category}:{prompt_hash}"
        await self.redis.setex(emb_key, ttl, json.dumps(embedding))

        # Store response
        resp_key = f"{RESPONSE_PREFIX}{category}:{prompt_hash}"
        response_data = {
            "response": req.response,
            "model": req.model,
            "tokens_used": req.tokens_used,
            "hit_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "metadata": req.metadata,
        }
        await self.redis.setex(resp_key, ttl, json.dumps(response_data))

        # Track in category index
        await self.redis.sadd(f"{INDEX_KEY}:{category}", prompt_hash)

        CACHE_ENTRIES.labels(category=category).inc()

        logger.info("cache_stored", category=category, hash=prompt_hash[:12], ttl=ttl)

        return {"status": "stored", "cache_key": prompt_hash, "ttl_seconds": ttl}

    async def invalidate_category(self, category: str) -> Dict[str, Any]:
        """Invalidate all cache entries for a category."""
        pattern = f"{EMBEDDING_PREFIX}{category}:*"
        resp_pattern = f"{RESPONSE_PREFIX}{category}:*"
        deleted = 0

        for pat in [pattern, resp_pattern]:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor=cursor, match=pat, count=100)
                if keys:
                    await self.redis.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break

        await self.redis.delete(f"{INDEX_KEY}:{category}")
        CACHE_ENTRIES.labels(category=category).set(0)

        logger.info("cache_invalidated", category=category, entries_deleted=deleted)
        return {"status": "invalidated", "category": category, "entries_deleted": deleted}

    async def invalidate_all(self) -> Dict[str, Any]:
        """Flush the entire semantic cache."""
        total_deleted = 0
        for category in CacheCategory:
            result = await self.invalidate_category(category.value)
            total_deleted += result["entries_deleted"]

        # Also flush stats
        await self.redis.delete(STATS_KEY)
        self._total_hits = 0
        self._total_misses = 0
        self._total_cost_saved = 0.0
        self._total_latency_saved = 0.0

        logger.info("cache_flushed", total_deleted=total_deleted)
        return {"status": "flushed", "total_deleted": total_deleted}

    async def get_stats(self) -> CacheStatsResponse:
        """Get cache statistics."""
        entries_per_category: Dict[str, int] = {}

        for category in CacheCategory:
            cat = category.value
            pattern = f"{EMBEDDING_PREFIX}{cat}:*"
            count = 0
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=500)
                count += len(keys)
                if cursor == 0:
                    break
            entries_per_category[cat] = count

        total_entries = sum(entries_per_category.values())
        total_requests = self._total_hits + self._total_misses
        hit_rate = (self._total_hits / total_requests * 100) if total_requests > 0 else 0.0

        return CacheStatsResponse(
            total_entries=total_entries,
            entries_per_category=entries_per_category,
            total_hits=self._total_hits,
            total_misses=self._total_misses,
            hit_rate=round(hit_rate, 2),
            estimated_cost_saved_usd=round(self._total_cost_saved, 4),
            estimated_latency_saved_seconds=round(self._total_latency_saved, 2),
            similarity_threshold=SIMILARITY_THRESHOLD,
        )

    def _update_hit_rate(self) -> None:
        """Update the hit rate gauge."""
        total = self._total_hits + self._total_misses
        rate = (self._total_hits / total * 100) if total > 0 else 0.0
        CACHE_HIT_RATE.set(round(rate, 2))


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────────────────────

engine = SemanticCacheEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await engine.initialize()
    logger.info("semantic_cache_started", port=9440)
    yield
    await engine.shutdown()


app = FastAPI(
    title="Semantic Cache",
    description="Redis-backed embedding similarity cache — 20-40% LLM cost reduction",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check."""
    return HealthResponse(status="healthy", service="semantic-cache", version="2.0.0")


@app.get("/ready")
async def ready():
    """Readiness check — verifies Redis connectivity."""
    try:
        await engine.redis.ping()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")


@app.post("/cache/check", response_model=CacheCheckResponse)
async def cache_check(req: CacheCheckRequest):
    """Check cache for a semantically similar prompt. Returns hit/miss + cached response."""
    return await engine.check(req)


@app.post("/cache/store")
async def cache_store(req: CacheStoreRequest):
    """Store a new LLM response in the cache."""
    return await engine.store(req)


@app.delete("/cache/invalidate/{category}")
async def cache_invalidate_category(category: str):
    """Invalidate all cache entries for a category."""
    if category not in [c.value for c in CacheCategory]:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    return await engine.invalidate_category(category)


@app.delete("/cache/invalidate/all")
async def cache_invalidate_all():
    """Flush the entire semantic cache."""
    return await engine.invalidate_all()


@app.get("/cache/stats", response_model=CacheStatsResponse)
async def cache_stats():
    """Get cache hit/miss rate, entries per category, estimated savings."""
    return await engine.get_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9440)
