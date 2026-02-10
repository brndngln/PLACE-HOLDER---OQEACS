#!/usr/bin/env python3
"""
SYSTEM 15 — INTEGRATION HUB: Nango SDK Client
Omni Quantum Elite AI Coding System — Communication & Workflow Layer

Async Python client for the Nango REST API.  Provides methods for
managing connections, triggering syncs, and retrieving records.

Requirements: httpx, structlog
"""

import asyncio
from types import TracebackType
from typing import Any, Self

import httpx
import structlog

log = structlog.get_logger(service="nango-client", system="15", component="integration-hub")


class NangoClient:
    """Async Nango REST API client with retry logic and structured logging.

    Usage::

        async with NangoClient("http://omni-nango:3003", secret_key) as nango:
            connections = await nango.list_connections()
    """

    def __init__(
        self,
        base_url: str,
        secret_key: str,
        *,
        max_retries: int = 3,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.secret_key = secret_key
        self.max_retries = max_retries
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        log.info("client_opened", base_url=self.base_url)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client:
            await self._client.aclose()
            log.info("client_closed")

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Issue an HTTP request with exponential-backoff retry."""
        assert self._client is not None, "Client not opened — use 'async with'"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = await self._client.request(method, path, **kwargs)
                if resp.status_code >= 500:
                    last_exc = httpx.HTTPStatusError(
                        f"Server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    log.warning("request_retry", path=path, attempt=attempt + 1, status=resp.status_code)
                    await asyncio.sleep(min(2 ** attempt, 8))
                    continue
                resp.raise_for_status()
                return resp
            except httpx.TransportError as exc:
                last_exc = exc
                log.warning("transport_error_retry", path=path, attempt=attempt + 1, error=str(exc))
                await asyncio.sleep(min(2 ** attempt, 8))
        raise last_exc  # type: ignore[misc]

    # -- Public API -----------------------------------------------------------

    async def list_connections(self) -> list[dict[str, Any]]:
        """List all active Nango connections.

        Returns:
            List of connection objects with provider, connection_id, and status.
        """
        resp = await self._request("GET", "/connection")
        result = resp.json()
        connections = result.get("connections", result) if isinstance(result, dict) else result
        log.info("connections_listed", count=len(connections))
        return connections

    async def get_connection(self, provider: str, connection_id: str = "default") -> dict[str, Any]:
        """Get details for a specific connection.

        Args:
            provider: Provider config key (e.g. ``"github"``, ``"stripe"``).
            connection_id: Connection identifier (default ``"default"``).

        Returns:
            Connection object with credentials and metadata.
        """
        resp = await self._request("GET", f"/connection/{connection_id}", params={"provider_config_key": provider})
        log.info("connection_retrieved", provider=provider, connection_id=connection_id)
        return resp.json()

    async def trigger_sync(self, provider: str, connection_id: str = "default") -> dict[str, Any]:
        """Trigger an immediate sync for a provider connection.

        Args:
            provider: Provider config key.
            connection_id: Connection identifier.

        Returns:
            Sync trigger response.
        """
        resp = await self._request(
            "POST",
            "/sync/trigger",
            json={
                "provider_config_key": provider,
                "connection_id": connection_id,
            },
        )
        log.info("sync_triggered", provider=provider, connection_id=connection_id)
        return resp.json()

    async def get_records(
        self,
        provider: str,
        model: str,
        connection_id: str = "default",
        *,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve synced records for a provider model.

        Args:
            provider: Provider config key.
            model: Data model name (e.g. ``"repos"``, ``"payments"``).
            connection_id: Connection identifier.
            limit: Maximum records to return.
            cursor: Pagination cursor from previous response.

        Returns:
            Dict with ``records`` list and optional ``next_cursor``.
        """
        params: dict[str, Any] = {
            "model": model,
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor

        resp = await self._request(
            "GET",
            f"/records",
            params={
                "model": model,
                "connection_id": connection_id,
                "provider_config_key": provider,
                "limit": limit,
                **({"cursor": cursor} if cursor else {}),
            },
        )
        data = resp.json()
        records = data.get("records", data) if isinstance(data, dict) else data
        log.info("records_retrieved", provider=provider, model=model, count=len(records) if isinstance(records, list) else 1)
        return data

    async def create_connection(
        self,
        provider: str,
        credentials: dict[str, Any],
        connection_id: str = "default",
    ) -> dict[str, Any]:
        """Create a new connection with provided credentials.

        Args:
            provider: Provider config key.
            credentials: Provider-specific credentials (API keys, tokens, etc.).
            connection_id: Connection identifier.

        Returns:
            Created connection object.
        """
        resp = await self._request(
            "POST",
            "/connection",
            json={
                "provider_config_key": provider,
                "connection_id": connection_id,
                "credentials": credentials,
            },
        )
        log.info("connection_created", provider=provider, connection_id=connection_id)
        return resp.json()
