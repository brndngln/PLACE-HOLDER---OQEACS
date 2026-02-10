"""
System 27 -- Token Infinity: Provider Router Service
Omni Quantum Elite AI Coding System

Intelligent LLM provider routing with health scoring, failover chains,
and tier-based selection. Routes requests to the optimal provider based on
task complexity, latency requirements, provider health, and cost.

Port: 9601
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx
import structlog
import yaml
from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("token_infinity.provider_router")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://omni-qdrant:6333")
LITELLM_URL: str = os.getenv("LITELLM_URL", "http://omni-litellm:4000")
OLLAMA_MANAGER_URL: str = os.getenv("OLLAMA_MANAGER_URL", "http://omni-model-manager:11435")
LANGFUSE_URL: str = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
VAULT_URL: str = os.getenv("VAULT_URL", "http://omni-vault:8200")
MATTERMOST_WEBHOOK_URL: str = os.getenv("MATTERMOST_WEBHOOK_URL", "http://omni-mattermost-webhook:8066")
PROVIDER_REGISTRY_PATH: str = os.getenv(
    "PROVIDER_REGISTRY_PATH", "/app/config/provider-registry.yaml"
)

SERVICE_NAME: str = "token-infinity-provider-router"
SERVICE_VERSION: str = "1.0.0"

HEALTH_CHECK_INTERVAL_SECONDS: int = 60
MAX_FAILOVER_ATTEMPTS: int = 3
UNHEALTHY_THRESHOLD: float = 0.3

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
registry = CollectorRegistry()

PROVIDER_REQUESTS_TOTAL = Counter(
    "provider_requests_total",
    "Total requests to providers",
    labelnames=["provider", "model", "status"],
    registry=registry,
)
PROVIDER_LATENCY = Histogram(
    "provider_latency_seconds",
    "Request latency per provider",
    labelnames=["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=registry,
)
PROVIDER_HEALTH_SCORE_GAUGE = Gauge(
    "provider_health_score",
    "Current health score for each provider",
    labelnames=["provider"],
    registry=registry,
)
PROVIDER_FAILOVERS = Counter(
    "provider_failovers_total",
    "Total failover events",
    labelnames=["from_provider", "to_provider"],
    registry=registry,
)
ROUTING_DECISIONS = Counter(
    "routing_decisions_total",
    "Total routing decisions made",
    labelnames=["tier", "provider"],
    registry=registry,
)
REQUESTS_TOTAL = Counter(
    "router_requests_total",
    "Total HTTP requests handled",
    labelnames=["endpoint", "status"],
    registry=registry,
)

# ---------------------------------------------------------------------------
# Enums and constants
# ---------------------------------------------------------------------------

class ProviderTier(str, Enum):
    LOCAL = "LOCAL"
    HIGH_SPEED = "HIGH_SPEED"
    AGGREGATOR = "AGGREGATOR"
    COMMUNITY = "COMMUNITY"


class TaskType(str, Enum):
    FEATURE_BUILD = "feature-build"
    BUG_FIX = "bug-fix"
    REFACTOR = "refactor"
    TEST_GEN = "test-gen"
    REVIEW = "review"
    DOCUMENTATION = "documentation"


class Complexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Estimated latencies per tier (ms)
TIER_ESTIMATED_LATENCY: dict[str, int] = {
    "LOCAL": 500,
    "HIGH_SPEED": 1000,
    "AGGREGATOR": 2000,
    "COMMUNITY": 5000,
}

# Model selection by complexity for local Ollama tier
LOCAL_MODEL_MAP: dict[str, list[str]] = {
    "critical": ["devstral-2", "deepseek-v3.2"],
    "high": ["devstral-2", "deepseek-v3.2"],
    "medium": ["qwen3-coder", "deepseek"],
    "low": ["devstral-small", "qwen3-coder"],
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RouteRequest(BaseModel):
    """Request body for POST /route."""
    complexity: Complexity
    task_type: TaskType
    max_latency_ms: Optional[int] = None
    required_context_length: Optional[int] = None


class FallbackEntry(BaseModel):
    """A single fallback option in the routing chain."""
    provider: str
    model: str
    tier: str
    estimated_latency_ms: int
    estimated_cost: float


class RouteResponse(BaseModel):
    """Response body for POST /route."""
    provider: str
    model: str
    estimated_latency_ms: int
    estimated_cost: float
    fallback_chain: list[FallbackEntry]


class ProviderConfig(BaseModel):
    """Configuration for a single provider from the registry."""
    name: str
    tier: ProviderTier
    priority: int
    endpoint: str
    manager_url: Optional[str] = None
    vault_path: Optional[str] = None
    rate_limit: int = 60
    cost_per_1k_tokens: float = 0.0
    max_context: int = 131_072
    models: list[str] = Field(default_factory=list)
    enabled: bool = True


class ProviderHealthData(BaseModel):
    """Runtime health data for a provider."""
    name: str
    tier: str
    enabled: bool
    health_score: float
    success_rate: float
    avg_latency_ms: float
    availability: float
    cost_score: float
    total_requests: int
    failed_requests: int
    last_checked: str
    models: list[str]


class ProviderStatusResponse(BaseModel):
    """Response for GET /providers."""
    providers: list[ProviderHealthData]


class ProviderHealthResponse(BaseModel):
    """Response for GET /providers/{name}/health."""
    provider: ProviderHealthData


class RoutingStatsResponse(BaseModel):
    """Response for GET /routing/stats."""
    period_hours: int
    total_decisions: int
    decisions_by_tier: dict[str, int]
    decisions_by_provider: dict[str, int]
    failover_count: int
    avg_health_scores: dict[str, float]


class ToggleResponse(BaseModel):
    """Response for provider enable/disable."""
    provider: str
    enabled: bool
    message: str


class HealthResponse(BaseModel):
    """Standard health check response."""
    status: str
    service: str
    version: str
    timestamp: str
    providers_loaded: int


class ReadyResponse(BaseModel):
    """Readiness check response."""
    ready: bool
    checks: dict[str, bool]


# ---------------------------------------------------------------------------
# Provider health tracker
# ---------------------------------------------------------------------------

class ProviderHealthTracker:
    """Tracks and scores provider health metrics in-memory.

    Maintains rolling statistics for each provider including success rates,
    latency averages, and availability. Computes a composite health score
    used for routing decisions.

    Attributes:
        configs: Mapping of provider name to configuration.
        health: Mapping of provider name to health data dictionary.
        routing_log: List of recent routing decisions.
    """

    def __init__(self) -> None:
        self.configs: dict[str, ProviderConfig] = {}
        self.health: dict[str, dict[str, Any]] = {}
        self.routing_log: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    def load_registry(self, path: str) -> None:
        """Load provider configurations from the YAML registry file.

        Args:
            path: Absolute path to provider-registry.yaml.
        """
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning("provider_registry_not_found", path=path)
            data = {"providers": []}

        providers_raw = data.get("providers", [])
        for p in providers_raw:
            config = ProviderConfig(
                name=p["name"],
                tier=ProviderTier(p["tier"]),
                priority=p.get("priority", 99),
                endpoint=p.get("endpoint", ""),
                manager_url=p.get("manager_url"),
                vault_path=p.get("vault_path"),
                rate_limit=p.get("rate_limit", 60),
                cost_per_1k_tokens=p.get("cost_per_1k_tokens", 0.0),
                max_context=p.get("max_context", 131_072),
                models=p.get("models", []),
                enabled=p.get("enabled", True),
            )
            self.configs[config.name] = config
            self.health[config.name] = {
                "total_requests": 0,
                "failed_requests": 0,
                "latency_sum_ms": 0.0,
                "latency_count": 0,
                "last_success": None,
                "last_failure": None,
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "available": True,
                "health_score": 1.0,
            }
            PROVIDER_HEALTH_SCORE_GAUGE.labels(provider=config.name).set(1.0)

        logger.info("provider_registry_loaded", count=len(self.configs))

    def compute_health_score(self, name: str) -> float:
        """Compute the composite health score for a provider.

        Score = success_rate * 0.4 + latency_score * 0.3 +
                availability * 0.2 + cost_score * 0.1

        Args:
            name: Provider name.

        Returns:
            Health score between 0.0 and 1.0.
        """
        h = self.health.get(name)
        config = self.configs.get(name)
        if not h or not config:
            return 0.0

        # Success rate
        total = h["total_requests"]
        failed = h["failed_requests"]
        success_rate = ((total - failed) / total) if total > 0 else 1.0

        # Latency score: lower is better; normalise against 10s ceiling
        if h["latency_count"] > 0:
            avg_latency_ms = h["latency_sum_ms"] / h["latency_count"]
            latency_score = max(0.0, 1.0 - (avg_latency_ms / 10_000.0))
        else:
            latency_score = 1.0

        # Availability
        availability = 1.0 if h["available"] else 0.0

        # Cost score: lower cost is better; normalise against $0.01/1k tokens
        cost = config.cost_per_1k_tokens
        cost_score = max(0.0, 1.0 - (cost / 0.01)) if cost > 0 else 1.0

        score = (
            success_rate * 0.4
            + latency_score * 0.3
            + availability * 0.2
            + cost_score * 0.1
        )
        score = max(0.0, min(1.0, score))

        h["health_score"] = score
        PROVIDER_HEALTH_SCORE_GAUGE.labels(provider=name).set(score)

        return score

    async def record_request(
        self, name: str, success: bool, latency_ms: float
    ) -> None:
        """Record the outcome of a request to a provider.

        Args:
            name: Provider name.
            success: Whether the request succeeded.
            latency_ms: Measured latency in milliseconds.
        """
        async with self._lock:
            h = self.health.get(name)
            if not h:
                return
            h["total_requests"] += 1
            if not success:
                h["failed_requests"] += 1
                h["last_failure"] = datetime.now(timezone.utc).isoformat()
            else:
                h["last_success"] = datetime.now(timezone.utc).isoformat()
            h["latency_sum_ms"] += latency_ms
            h["latency_count"] += 1
            h["last_checked"] = datetime.now(timezone.utc).isoformat()

            self.compute_health_score(name)

    async def record_routing_decision(
        self, provider: str, model: str, tier: str
    ) -> None:
        """Record a routing decision for statistics.

        Args:
            provider: Selected provider name.
            model: Selected model name.
            tier: Provider tier.
        """
        async with self._lock:
            self.routing_log.append({
                "provider": provider,
                "model": model,
                "tier": tier,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            # Keep only last 10,000 decisions
            if len(self.routing_log) > 10_000:
                self.routing_log = self.routing_log[-10_000:]

            ROUTING_DECISIONS.labels(tier=tier, provider=provider).inc()

    def get_provider_health(self, name: str) -> Optional[ProviderHealthData]:
        """Get current health data for a provider.

        Args:
            name: Provider name.

        Returns:
            ProviderHealthData or None if provider not found.
        """
        config = self.configs.get(name)
        h = self.health.get(name)
        if not config or not h:
            return None

        total = h["total_requests"]
        failed = h["failed_requests"]
        success_rate = ((total - failed) / total) if total > 0 else 1.0

        avg_latency = (
            (h["latency_sum_ms"] / h["latency_count"])
            if h["latency_count"] > 0
            else 0.0
        )

        cost = config.cost_per_1k_tokens
        cost_score = max(0.0, 1.0 - (cost / 0.01)) if cost > 0 else 1.0

        return ProviderHealthData(
            name=config.name,
            tier=config.tier.value,
            enabled=config.enabled,
            health_score=h["health_score"],
            success_rate=round(success_rate, 4),
            avg_latency_ms=round(avg_latency, 2),
            availability=1.0 if h["available"] else 0.0,
            cost_score=round(cost_score, 4),
            total_requests=total,
            failed_requests=failed,
            last_checked=h["last_checked"],
            models=config.models,
        )

    def get_all_providers(self) -> list[ProviderHealthData]:
        """Get health data for all registered providers.

        Returns:
            List of ProviderHealthData for every provider.
        """
        result: list[ProviderHealthData] = []
        for name in sorted(self.configs.keys()):
            data = self.get_provider_health(name)
            if data:
                result.append(data)
        return result

    def get_routing_stats(self, hours: int = 24) -> RoutingStatsResponse:
        """Compute routing statistics over a time window.

        Args:
            hours: Number of hours to look back.

        Returns:
            Aggregated routing statistics.
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        recent = [
            d for d in self.routing_log
            if datetime.fromisoformat(d["timestamp"]).timestamp() >= cutoff
        ]

        decisions_by_tier: dict[str, int] = defaultdict(int)
        decisions_by_provider: dict[str, int] = defaultdict(int)
        for d in recent:
            decisions_by_tier[d["tier"]] += 1
            decisions_by_provider[d["provider"]] += 1

        # Count failovers (simple: decisions where provider != first choice)
        failover_count = 0
        for i, d in enumerate(recent):
            if i > 0 and recent[i - 1].get("provider") != d.get("provider"):
                failover_count += 1

        avg_scores: dict[str, float] = {}
        for name in self.configs:
            avg_scores[name] = round(self.health[name]["health_score"], 4)

        return RoutingStatsResponse(
            period_hours=hours,
            total_decisions=len(recent),
            decisions_by_tier=dict(decisions_by_tier),
            decisions_by_provider=dict(decisions_by_provider),
            failover_count=failover_count,
            avg_health_scores=avg_scores,
        )


# ---------------------------------------------------------------------------
# HTTP client helpers
# ---------------------------------------------------------------------------

def _build_http_client(timeout: float = 15.0) -> httpx.AsyncClient:
    """Build a configured httpx.AsyncClient with retry transport.

    Args:
        timeout: Total request timeout in seconds.

    Returns:
        Configured async HTTP client.
    """
    transport = httpx.AsyncHTTPTransport(retries=3)
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=5.0),
        transport=transport,
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

tracker = ProviderHealthTracker()
_health_check_task: Optional[asyncio.Task[None]] = None


# ---------------------------------------------------------------------------
# Background health checker
# ---------------------------------------------------------------------------

async def _periodic_health_check() -> None:
    """Background task that checks provider health every 60 seconds.

    Pings each provider's endpoint and updates availability and health scores.
    Providers with a score below UNHEALTHY_THRESHOLD are marked unavailable.
    """
    while True:
        try:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
            async with _build_http_client(timeout=10.0) as client:
                for name, config in tracker.configs.items():
                    if not config.enabled:
                        tracker.health[name]["available"] = False
                        tracker.compute_health_score(name)
                        continue

                    start = time.monotonic()
                    available = False

                    try:
                        if config.tier == ProviderTier.LOCAL:
                            # Check Ollama manager
                            url = config.manager_url or f"{OLLAMA_MANAGER_URL}/health"
                            resp = await client.get(url)
                            available = resp.status_code == 200
                        else:
                            # For remote providers, verify LiteLLM can reach them
                            resp = await client.get(f"{LITELLM_URL}/health/liveliness")
                            available = resp.status_code == 200
                    except httpx.HTTPError:
                        available = False

                    latency_ms = (time.monotonic() - start) * 1000
                    tracker.health[name]["available"] = available
                    tracker.health[name]["last_checked"] = datetime.now(timezone.utc).isoformat()

                    score = tracker.compute_health_score(name)

                    # Temporarily remove providers with very low scores
                    if score < UNHEALTHY_THRESHOLD:
                        tracker.health[name]["available"] = False
                        logger.warning(
                            "provider_unhealthy",
                            provider=name,
                            score=round(score, 4),
                            threshold=UNHEALTHY_THRESHOLD,
                        )

                    logger.debug(
                        "health_check_complete",
                        provider=name,
                        available=available,
                        score=round(score, 4),
                        latency_ms=round(latency_ms, 1),
                    )

        except asyncio.CancelledError:
            logger.info("health_check_task_cancelled")
            break
        except Exception as exc:
            logger.exception("health_check_error", error=str(exc))


# ---------------------------------------------------------------------------
# Ollama model discovery
# ---------------------------------------------------------------------------

async def _get_loaded_ollama_models(client: httpx.AsyncClient) -> list[str]:
    """Query the Ollama model manager for currently loaded models.

    Args:
        client: Shared HTTP client.

    Returns:
        List of loaded model names.
    """
    try:
        resp = await client.get(f"{OLLAMA_MANAGER_URL}/models")
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", data.get("loaded", []))
            if isinstance(models, list):
                return [
                    m.get("name", m) if isinstance(m, dict) else str(m)
                    for m in models
                ]
        logger.warning("ollama_model_list_failed", status=resp.status_code)
    except httpx.HTTPError as exc:
        logger.warning("ollama_model_list_error", error=str(exc))
    return []


# ---------------------------------------------------------------------------
# Routing engine
# ---------------------------------------------------------------------------

async def route_request(req: RouteRequest) -> RouteResponse:
    """Route a request to the best available provider.

    Selection algorithm:
        1. Build candidate list sorted by tier priority and health score.
        2. Filter by max_latency_ms if specified.
        3. Filter by required_context_length if specified.
        4. Select model based on complexity for local providers.
        5. Build fallback chain from remaining candidates.

    Args:
        req: The routing request.

    Returns:
        RouteResponse with selected provider and fallback chain.

    Raises:
        HTTPException: If no healthy providers are available.
    """
    log = logger.bind(complexity=req.complexity.value, task_type=req.task_type.value)
    log.info("routing_request_received")

    # Fetch loaded Ollama models for local tier
    loaded_ollama_models: list[str] = []
    async with _build_http_client(timeout=5.0) as client:
        loaded_ollama_models = await _get_loaded_ollama_models(client)

    # Build candidates
    candidates: list[dict[str, Any]] = []

    for name, config in tracker.configs.items():
        if not config.enabled:
            continue

        h = tracker.health.get(name, {})
        if not h.get("available", False):
            continue

        score = h.get("health_score", 0.0)
        if score < UNHEALTHY_THRESHOLD:
            continue

        tier_latency = TIER_ESTIMATED_LATENCY.get(config.tier.value, 5000)

        # Filter by max latency
        if req.max_latency_ms and tier_latency > req.max_latency_ms:
            continue

        # Filter by context length
        if req.required_context_length and req.required_context_length > config.max_context:
            continue

        # Determine model for this provider
        if config.tier == ProviderTier.LOCAL:
            # Select model based on complexity
            preferred = LOCAL_MODEL_MAP.get(req.complexity.value, ["devstral-small"])
            selected_model = None
            for m in preferred:
                if m in loaded_ollama_models:
                    selected_model = m
                    break
            if not selected_model:
                # Try any loaded model
                if loaded_ollama_models:
                    selected_model = loaded_ollama_models[0]
                else:
                    continue  # No models available
        else:
            # Use first model from config
            selected_model = config.models[0] if config.models else "default"

        candidates.append({
            "provider": name,
            "model": selected_model,
            "tier": config.tier.value,
            "priority": config.priority,
            "health_score": score,
            "estimated_latency_ms": tier_latency,
            "estimated_cost": config.cost_per_1k_tokens,
        })

    if not candidates:
        log.error("no_healthy_providers")
        raise HTTPException(
            status_code=503,
            detail="No healthy providers available. All providers are either disabled, unhealthy, or do not meet requirements.",
        )

    # Sort by priority (ascending), then health score (descending)
    candidates.sort(key=lambda c: (c["priority"], -c["health_score"]))

    # Select primary
    primary = candidates[0]

    # Build fallback chain from remaining candidates (up to MAX_FAILOVER_ATTEMPTS)
    fallback_chain: list[FallbackEntry] = []
    seen_providers: set[str] = {primary["provider"]}

    for c in candidates[1:]:
        if c["provider"] in seen_providers:
            continue
        if len(fallback_chain) >= MAX_FAILOVER_ATTEMPTS:
            break
        fallback_chain.append(FallbackEntry(
            provider=c["provider"],
            model=c["model"],
            tier=c["tier"],
            estimated_latency_ms=c["estimated_latency_ms"],
            estimated_cost=c["estimated_cost"],
        ))
        seen_providers.add(c["provider"])

    # Record the routing decision
    await tracker.record_routing_decision(
        provider=primary["provider"],
        model=primary["model"],
        tier=primary["tier"],
    )

    log.info(
        "routing_decision_made",
        provider=primary["provider"],
        model=primary["model"],
        tier=primary["tier"],
        health_score=primary["health_score"],
        fallbacks=len(fallback_chain),
    )

    PROVIDER_REQUESTS_TOTAL.labels(
        provider=primary["provider"],
        model=primary["model"],
        status="routed",
    ).inc()

    return RouteResponse(
        provider=primary["provider"],
        model=primary["model"],
        estimated_latency_ms=primary["estimated_latency_ms"],
        estimated_cost=primary["estimated_cost"],
        fallback_chain=fallback_chain,
    )


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    global _health_check_task

    logger.info("provider_router_starting", port=9601, version=SERVICE_VERSION)

    # Load provider registry
    tracker.load_registry(PROVIDER_REGISTRY_PATH)

    # Start background health checker
    _health_check_task = asyncio.create_task(_periodic_health_check())

    yield

    # Shutdown
    if _health_check_task:
        _health_check_task.cancel()
        try:
            await _health_check_task
        except asyncio.CancelledError:
            pass
    logger.info("provider_router_shutting_down")


app = FastAPI(
    title="Token Infinity -- Provider Router",
    description=(
        "Intelligent LLM provider routing with health scoring, failover chains, "
        "and tier-based selection for the Omni Quantum Elite AI Coding System."
    ),
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/route", response_model=RouteResponse)
async def endpoint_route(req: RouteRequest) -> RouteResponse:
    """Route a request to the best available LLM provider.

    Evaluates all registered providers based on health scores, latency
    constraints, context length requirements, and task complexity to select
    the optimal provider. Includes a prioritised fallback chain.
    """
    REQUESTS_TOTAL.labels(endpoint="/route", status="started").inc()
    try:
        result = await route_request(req)
        REQUESTS_TOTAL.labels(endpoint="/route", status="success").inc()
        return result
    except HTTPException:
        REQUESTS_TOTAL.labels(endpoint="/route", status="error").inc()
        raise
    except Exception as exc:
        REQUESTS_TOTAL.labels(endpoint="/route", status="error").inc()
        logger.exception("routing_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Routing failed: {exc}") from exc


@app.get("/providers", response_model=ProviderStatusResponse)
async def endpoint_list_providers() -> ProviderStatusResponse:
    """List all registered providers with their current health scores.

    Returns comprehensive health data for every provider in the registry,
    including success rates, latency averages, and availability status.
    """
    providers = tracker.get_all_providers()
    return ProviderStatusResponse(providers=providers)


@app.get("/providers/{name}/health", response_model=ProviderHealthResponse)
async def endpoint_provider_health(
    name: str = Path(..., description="Provider name"),
) -> ProviderHealthResponse:
    """Get detailed health information for a specific provider.

    Args:
        name: The provider identifier from the registry.
    """
    data = tracker.get_provider_health(name)
    if not data:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    return ProviderHealthResponse(provider=data)


@app.post("/providers/{name}/disable", response_model=ToggleResponse)
async def endpoint_disable_provider(
    name: str = Path(..., description="Provider name"),
) -> ToggleResponse:
    """Disable a provider, removing it from routing decisions.

    The provider remains registered but will not receive any requests
    until re-enabled.
    """
    config = tracker.configs.get(name)
    if not config:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")

    config.enabled = False
    tracker.health[name]["available"] = False
    tracker.compute_health_score(name)

    logger.info("provider_disabled", provider=name)

    return ToggleResponse(
        provider=name,
        enabled=False,
        message=f"Provider '{name}' has been disabled and removed from routing.",
    )


@app.post("/providers/{name}/enable", response_model=ToggleResponse)
async def endpoint_enable_provider(
    name: str = Path(..., description="Provider name"),
) -> ToggleResponse:
    """Re-enable a previously disabled provider.

    The provider will be included in the next health check cycle and,
    if healthy, will begin receiving requests again.
    """
    config = tracker.configs.get(name)
    if not config:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")

    config.enabled = True
    tracker.health[name]["available"] = True
    tracker.compute_health_score(name)

    logger.info("provider_enabled", provider=name)

    return ToggleResponse(
        provider=name,
        enabled=True,
        message=f"Provider '{name}' has been enabled and will be included in routing.",
    )


@app.get("/routing/stats", response_model=RoutingStatsResponse)
async def endpoint_routing_stats(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
) -> RoutingStatsResponse:
    """Get routing decision statistics over a time window.

    Provides aggregate counts of routing decisions by tier and provider,
    failover events, and average health scores for the specified period.
    """
    return tracker.get_routing_stats(hours)


@app.get("/health", response_model=HealthResponse)
async def endpoint_health() -> HealthResponse:
    """Service health check.

    Verifies that the provider router process is running and the registry
    is loaded.
    """
    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        providers_loaded=len(tracker.configs),
    )


@app.get("/ready", response_model=ReadyResponse)
async def endpoint_ready() -> ReadyResponse:
    """Readiness probe that verifies external dependency availability.

    Checks LiteLLM and Ollama Manager connectivity. The service is
    considered ready when at least one provider is healthy and dependencies
    are reachable.
    """
    checks: dict[str, bool] = {}

    async with _build_http_client(timeout=5.0) as client:
        # Check LiteLLM
        try:
            resp = await client.get(f"{LITELLM_URL}/health/liveliness")
            checks["litellm"] = resp.status_code == 200
        except httpx.HTTPError:
            checks["litellm"] = False

        # Check Ollama Manager
        try:
            resp = await client.get(f"{OLLAMA_MANAGER_URL}/health")
            checks["ollama_manager"] = resp.status_code == 200
        except httpx.HTTPError:
            checks["ollama_manager"] = False

    # Check if any providers are healthy
    healthy_providers = sum(
        1 for h in tracker.health.values()
        if h.get("available", False) and h.get("health_score", 0) >= UNHEALTHY_THRESHOLD
    )
    checks["healthy_providers"] = healthy_providers > 0

    all_ready = all(checks.values())
    if not all_ready:
        logger.warning("readiness_check_failed", checks=checks)

    return ReadyResponse(ready=all_ready, checks=checks)


@app.get("/metrics")
async def endpoint_metrics() -> JSONResponse:
    """Expose Prometheus metrics in text format."""
    metrics_output = generate_latest(registry)
    return JSONResponse(
        content={"metrics": metrics_output.decode("utf-8")},
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "service": SERVICE_NAME,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9601,
        log_level="info",
        access_log=True,
        reload=False,
        workers=1,
    )
