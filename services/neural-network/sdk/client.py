#!/usr/bin/env python3
"""
SYSTEM 8 — NEURAL NETWORK: Ollama Manager SDK Client
Omni Quantum Elite AI Coding System — AI Coding Pipeline

Async client for the Model Manager REST API. Typed Pydantic returns.

Requirements: httpx, structlog, pydantic
"""

import asyncio
from types import TracebackType
from typing import Any, Self

import httpx
import structlog
from pydantic import BaseModel, Field

log = structlog.get_logger(service="ollama-manager-client", system="8", component="neural-network")


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------
class ModelInfo(BaseModel):
    name: str
    status: str = "unknown"
    vram_bytes: int = 0
    vram_estimate_gb: float = 0
    load_time_seconds: float = 0
    request_count: int = 0
    error_count: int = 0
    tokens_per_second: float = 0
    context_length: int = 0
    priority: int = 99
    use_cases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    last_used: str | None = None
    loaded_at: str | None = None


class GPUStatus(BaseModel):
    vram_total_bytes: int = 0
    vram_used_bytes: int = 0
    vram_free_bytes: int = 0
    gpu_utilization_percent: float = 0
    temperature_celsius: float = 0


class BenchmarkResult(BaseModel):
    model: str
    tokens_per_second: float
    total_tokens: int
    duration_seconds: float
    prompt_tokens: int
    eval_tokens: int


class JobStatus(BaseModel):
    job_id: str
    model: str
    status: str
    progress: float = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class OllamaManagerClient:
    """Async client for the Ollama Model Manager service.

    Usage::

        async with OllamaManagerClient() as mgr:
            models = await mgr.list_models()
            rec = await mgr.get_recommended_model("code-generation")
    """

    def __init__(self, base_url: str = "http://localhost:11435", *, max_retries: int = 3, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        if self._client:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """HTTP request with exponential backoff retry."""
        assert self._client, "Client not opened — use 'async with'"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = await self._client.request(method, path, **kwargs)
                if resp.status_code >= 500 and attempt < self.max_retries - 1:
                    await asyncio.sleep(min(2 ** attempt, 8))
                    continue
                resp.raise_for_status()
                return resp
            except httpx.TransportError as exc:
                last_exc = exc
                await asyncio.sleep(min(2 ** attempt, 8))
        raise last_exc  # type: ignore[misc]

    async def list_models(self) -> list[ModelInfo]:
        """List all models with status, VRAM, and metrics."""
        resp = await self._request("GET", "/models")
        return [ModelInfo(**m) for m in resp.json()]

    async def get_model(self, name: str) -> ModelInfo:
        """Get detailed info for a specific model."""
        resp = await self._request("GET", f"/models/{name}")
        return ModelInfo(**resp.json())

    async def pull_model(self, name: str) -> JobStatus:
        """Pull a model asynchronously. Returns a job ID for tracking."""
        resp = await self._request("POST", "/models/pull", json={"name": name})
        return JobStatus(**resp.json())

    async def load_model(self, name: str) -> bool:
        """Load a model into VRAM. Returns True on success."""
        try:
            await self._request("POST", "/models/load", json={"name": name}, timeout=300.0)
            return True
        except httpx.HTTPStatusError:
            return False

    async def unload_model(self, name: str) -> bool:
        """Unload a model from VRAM. Returns True on success."""
        try:
            await self._request("POST", f"/models/unload/{name}")
            return True
        except httpx.HTTPStatusError:
            return False

    async def gpu_status(self) -> GPUStatus:
        """Get GPU VRAM and utilization stats."""
        resp = await self._request("GET", "/gpu/status")
        return GPUStatus(**resp.json())

    async def benchmark(self, name: str) -> BenchmarkResult:
        """Benchmark a model's tokens/sec on a standard prompt."""
        resp = await self._request("POST", f"/models/benchmark/{name}", timeout=120.0)
        return BenchmarkResult(**resp.json())

    async def get_recommended_model(self, use_case: str) -> str:
        """Recommend the best loaded model for a given use case.

        Args:
            use_case: Task category like ``"code-generation"``, ``"bug-fixing"``, etc.

        Returns:
            Model name string of the best match.
        """
        models = await self.list_models()
        loaded = [m for m in models if m.status == "loaded"]
        for m in sorted(loaded, key=lambda x: x.priority):
            if use_case in m.use_cases:
                return m.name
        if loaded:
            return sorted(loaded, key=lambda x: x.priority)[0].name
        raise RuntimeError("No models loaded")
