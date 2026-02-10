"""
System 27 -- Token Infinity: Python SDK Client
Omni Quantum Elite AI Coding System

Async client library for interacting with the Token Infinity context manager
and provider router services. Provides typed methods for context compilation,
token estimation, model recommendation, provider routing, and health monitoring.

Usage::

    async with TokenInfinityClient() as client:
        ctx = await client.compile_context(
            task_description="Implement user authentication",
            task_type="feature-build",
            complexity="high",
        )
        print(ctx.compiled_context)
        print(ctx.model_recommendation)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Optional

import httpx
import structlog
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
logger = structlog.get_logger("token_infinity.sdk")

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ContextBlock(BaseModel):
    """A single block within a compiled context."""
    type: str
    tokens: int
    source: str
    details: str
    truncated: bool = False


class CompiledContext(BaseModel):
    """Result of a context compilation request."""
    compiled_context: str
    model_recommendation: str
    token_count: int
    token_budget: int
    context_blocks: list[ContextBlock]
    trace_id: str


class TokenEstimate(BaseModel):
    """Result of a token estimation request."""
    estimated_tokens: int
    estimated_blocks: dict[str, int]
    recommended_model: str
    fits_in_budget: bool
    budget: int


class ModelRecommendation(BaseModel):
    """Result of a model recommendation request."""
    recommended_model: str
    context_window: int
    reasoning: str
    alternatives: list[str]


class FallbackEntry(BaseModel):
    """A single fallback option in a routing decision."""
    provider: str
    model: str
    tier: str
    estimated_latency_ms: int
    estimated_cost: float


class RoutingDecision(BaseModel):
    """Result of a routing request."""
    provider: str
    model: str
    estimated_latency_ms: int
    estimated_cost: float
    fallback_chain: list[FallbackEntry]


class ProviderStatus(BaseModel):
    """Health status of a single provider."""
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


class ProviderHealth(BaseModel):
    """Detailed health information for a single provider."""
    provider: ProviderStatus


class RoutingStats(BaseModel):
    """Aggregated routing statistics over a time window."""
    period_hours: int
    total_decisions: int
    decisions_by_tier: dict[str, int]
    decisions_by_provider: dict[str, int]
    failover_count: int
    avg_health_scores: dict[str, float]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TokenInfinityError(Exception):
    """Base exception for Token Infinity SDK errors.

    Attributes:
        status_code: HTTP status code from the upstream service.
        detail: Human-readable error description.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{status_code}] {detail}")


class ContextCompilationError(TokenInfinityError):
    """Raised when context compilation fails."""
    pass


class RoutingError(TokenInfinityError):
    """Raised when provider routing fails."""
    pass


class ProviderNotFoundError(TokenInfinityError):
    """Raised when a requested provider does not exist."""
    pass


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class TokenInfinityClient:
    """Async client for Token Infinity context manager and provider router.

    Implements the async context manager protocol for clean resource management.
    All methods include automatic retry logic (up to 3 attempts) with
    exponential backoff for transient failures.

    Args:
        base_url: Base URL for the context manager service (port 9600).
        router_url: Base URL for the provider router service (port 9601).
            If not provided, derived from base_url by replacing port 9600 with 9601.
        timeout: Default request timeout in seconds.
        max_retries: Maximum number of retry attempts for failed requests.

    Usage::

        async with TokenInfinityClient() as client:
            ctx = await client.compile_context(
                task_description="Build REST API endpoint",
                task_type="feature-build",
                complexity="medium",
            )
    """

    def __init__(
        self,
        base_url: str = "http://localhost:9600",
        router_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._router_url = (
            router_url.rstrip("/")
            if router_url
            else self._base_url.replace(":9600", ":9601")
        )
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._log = logger.bind(component="TokenInfinityClient")

    async def __aenter__(self) -> TokenInfinityClient:
        """Enter the async context manager and initialise the HTTP client."""
        transport = httpx.AsyncHTTPTransport(retries=2)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout, connect=10.0),
            transport=transport,
            follow_redirects=True,
        )
        self._log.info("client_initialised", base_url=self._base_url, router_url=self._router_url)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context manager and close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._log.info("client_closed")

    @property
    def client(self) -> httpx.AsyncClient:
        """Return the active HTTP client, raising if not initialised.

        Returns:
            The active httpx.AsyncClient instance.

        Raises:
            RuntimeError: If the client has not been initialised via ``async with``.
        """
        if self._client is None:
            raise RuntimeError(
                "TokenInfinityClient must be used as an async context manager. "
                "Use 'async with TokenInfinityClient() as client:'"
            )
        return self._client

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        json_body: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with exponential backoff retry logic.

        Retries on 5xx status codes, timeouts, and connection errors up to
        ``max_retries`` times with exponential backoff (1s, 2s, 4s, ...).

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full request URL.
            json_body: Optional JSON request body.
            params: Optional query parameters.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            TokenInfinityError: If all retry attempts fail.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                self._log.debug(
                    "request_attempt",
                    method=method,
                    url=url,
                    attempt=attempt,
                )

                if method.upper() == "GET":
                    resp = await self.client.get(url, params=params)
                elif method.upper() == "POST":
                    resp = await self.client.post(url, json=json_body, params=params)
                else:
                    resp = await self.client.request(method, url, json=json_body, params=params)

                if resp.status_code < 500:
                    # Non-retryable response (success or client error)
                    if resp.status_code >= 400:
                        detail = resp.text
                        try:
                            detail = resp.json().get("detail", resp.text)
                        except Exception:
                            pass
                        raise TokenInfinityError(resp.status_code, str(detail))

                    return resp.json()

                # 5xx -- retryable
                last_error = TokenInfinityError(resp.status_code, resp.text)
                self._log.warning(
                    "request_server_error",
                    status=resp.status_code,
                    attempt=attempt,
                    url=url,
                )

            except httpx.TimeoutException as exc:
                last_error = exc
                self._log.warning("request_timeout", attempt=attempt, url=url)
            except httpx.ConnectError as exc:
                last_error = exc
                self._log.warning("request_connection_error", attempt=attempt, url=url, error=str(exc))
            except TokenInfinityError:
                raise
            except httpx.HTTPError as exc:
                last_error = exc
                self._log.warning("request_http_error", attempt=attempt, url=url, error=str(exc))

            # Exponential backoff
            if attempt < self._max_retries:
                backoff = 2 ** (attempt - 1)
                await asyncio.sleep(backoff)

        # All retries exhausted
        error_msg = str(last_error) if last_error else "Unknown error"
        raise TokenInfinityError(502, f"All {self._max_retries} retry attempts failed: {error_msg}")

    # -----------------------------------------------------------------------
    # Context Manager endpoints
    # -----------------------------------------------------------------------

    async def compile_context(
        self,
        task_description: str,
        task_type: str,
        complexity: str,
        project_id: Optional[str] = None,
        referenced_files: Optional[list[str]] = None,
        target_model: Optional[str] = None,
    ) -> CompiledContext:
        """Compile an optimal context window for an AI task.

        Assembles context from multiple sources (referenced files, vector
        search results, design patterns, feedback) using priority-based
        filling within the target model's token budget.

        Args:
            task_description: Natural language description of the task.
            task_type: One of: feature-build, bug-fix, refactor, test-gen, review, documentation.
            complexity: One of: low, medium, high, critical.
            project_id: Optional Gitea repository identifier (owner/repo).
            referenced_files: Optional list of file paths to include.
            target_model: Optional specific model to target (overrides recommendation).

        Returns:
            CompiledContext with the full prompt, token counts, and block breakdown.

        Raises:
            ContextCompilationError: If compilation fails.
        """
        body: dict[str, Any] = {
            "task_description": task_description,
            "task_type": task_type,
            "complexity": complexity,
        }
        if project_id is not None:
            body["project_id"] = project_id
        if referenced_files is not None:
            body["referenced_files"] = referenced_files
        if target_model is not None:
            body["target_model"] = target_model

        try:
            data = await self._request_with_retry(
                "POST", f"{self._base_url}/context/compile", json_body=body,
            )
            return CompiledContext(**data)
        except TokenInfinityError as exc:
            raise ContextCompilationError(exc.status_code, exc.detail) from exc

    async def estimate_tokens(
        self,
        task_description: str,
        task_type: str = "feature-build",
        complexity: str = "medium",
        referenced_files: Optional[list[str]] = None,
    ) -> TokenEstimate:
        """Estimate token usage for a context compilation without executing it.

        Provides a quick estimate of how many tokens each context block type
        would consume, without actually querying external sources.

        Args:
            task_description: Natural language description of the task.
            task_type: One of: feature-build, bug-fix, refactor, test-gen, review, documentation.
            complexity: One of: low, medium, high, critical.
            referenced_files: Optional list of file paths to include.

        Returns:
            TokenEstimate with per-block estimates and budget information.
        """
        body: dict[str, Any] = {
            "task_description": task_description,
            "task_type": task_type,
            "complexity": complexity,
        }
        if referenced_files is not None:
            body["referenced_files"] = referenced_files

        data = await self._request_with_retry(
            "POST", f"{self._base_url}/context/estimate", json_body=body,
        )
        return TokenEstimate(**data)

    async def recommend_model(
        self,
        complexity: str,
        task_type: str,
    ) -> ModelRecommendation:
        """Get a model recommendation for a given complexity and task type.

        Returns the recommended model along with reasoning and alternative
        options based on task requirements.

        Args:
            complexity: One of: low, medium, high, critical.
            task_type: One of: feature-build, bug-fix, refactor, test-gen, review, documentation.

        Returns:
            ModelRecommendation with model name, reasoning, and alternatives.
        """
        params = {"complexity": complexity, "task_type": task_type}
        data = await self._request_with_retry(
            "GET", f"{self._base_url}/models/recommend", params=params,
        )
        return ModelRecommendation(**data)

    # -----------------------------------------------------------------------
    # Provider Router endpoints
    # -----------------------------------------------------------------------

    async def route_request(
        self,
        complexity: str,
        task_type: str,
        max_latency_ms: Optional[int] = None,
        required_context_length: Optional[int] = None,
    ) -> RoutingDecision:
        """Route a request to the best available LLM provider.

        Evaluates all registered providers based on health scores, latency
        constraints, and task complexity to select the optimal provider.

        Args:
            complexity: One of: low, medium, high, critical.
            task_type: One of: feature-build, bug-fix, refactor, test-gen, review, documentation.
            max_latency_ms: Optional maximum acceptable latency in milliseconds.
            required_context_length: Optional minimum context window length in tokens.

        Returns:
            RoutingDecision with provider, model, and fallback chain.

        Raises:
            RoutingError: If no healthy providers are available.
        """
        body: dict[str, Any] = {
            "complexity": complexity,
            "task_type": task_type,
        }
        if max_latency_ms is not None:
            body["max_latency_ms"] = max_latency_ms
        if required_context_length is not None:
            body["required_context_length"] = required_context_length

        try:
            data = await self._request_with_retry(
                "POST", f"{self._router_url}/route", json_body=body,
            )
            return RoutingDecision(**data)
        except TokenInfinityError as exc:
            raise RoutingError(exc.status_code, exc.detail) from exc

    async def list_providers(self) -> list[ProviderStatus]:
        """List all registered providers with their current health scores.

        Returns:
            List of ProviderStatus objects for every provider in the registry.
        """
        data = await self._request_with_retry(
            "GET", f"{self._router_url}/providers",
        )
        providers_raw = data.get("providers", [])
        return [ProviderStatus(**p) for p in providers_raw]

    async def provider_health(self, name: str) -> ProviderHealth:
        """Get detailed health information for a specific provider.

        Args:
            name: The provider identifier from the registry.

        Returns:
            ProviderHealth with comprehensive health metrics.

        Raises:
            ProviderNotFoundError: If the provider does not exist.
        """
        try:
            data = await self._request_with_retry(
                "GET", f"{self._router_url}/providers/{name}/health",
            )
            return ProviderHealth(**data)
        except TokenInfinityError as exc:
            if exc.status_code == 404:
                raise ProviderNotFoundError(404, f"Provider '{name}' not found") from exc
            raise

    async def routing_stats(self, hours: int = 24) -> RoutingStats:
        """Get routing decision statistics over a time window.

        Args:
            hours: Number of hours to look back (1-168). Defaults to 24.

        Returns:
            RoutingStats with aggregate counts and health score averages.
        """
        data = await self._request_with_retry(
            "GET", f"{self._router_url}/routing/stats", params={"hours": hours},
        )
        return RoutingStats(**data)

    # -----------------------------------------------------------------------
    # Health checks
    # -----------------------------------------------------------------------

    async def context_manager_healthy(self) -> bool:
        """Check if the context manager service is healthy.

        Returns:
            True if the service is healthy, False otherwise.
        """
        try:
            data = await self._request_with_retry(
                "GET", f"{self._base_url}/health",
            )
            return data.get("status") == "healthy"
        except Exception:
            return False

    async def provider_router_healthy(self) -> bool:
        """Check if the provider router service is healthy.

        Returns:
            True if the service is healthy, False otherwise.
        """
        try:
            data = await self._request_with_retry(
                "GET", f"{self._router_url}/health",
            )
            return data.get("status") == "healthy"
        except Exception:
            return False
