#!/usr/bin/env python3
"""
SYSTEM 28 — OMI WEARABLE BRIDGE: SDK Client
Omni Quantum Elite AI Coding System — Communication & Workflow Layer

Async Python client for the Omi Bridge REST API.  Provides methods for
sending haptic patterns, voice commands, and checking device status.

Requirements: httpx, structlog
"""

import asyncio
from types import TracebackType
from typing import Any, Self

import httpx
import structlog

log = structlog.get_logger(service="omi-bridge-client", system="28", component="omi-bridge")


class OmiBridgeClient:
    """Async client for the Omi Wearable Bridge service.

    Usage::

        async with OmiBridgeClient("http://omni-omi-bridge:9700") as omi:
            await omi.send_haptic("critical", message="Server down!")
    """

    def __init__(
        self,
        base_url: str,
        *,
        max_retries: int = 3,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
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

    async def send_haptic(
        self,
        pattern: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        """Send a haptic notification to the Omi device.

        Args:
            pattern: Haptic pattern name (``critical``, ``warning``, ``info``,
                     ``build-complete``, ``deploy-success``, ``test-failure``).
            message: Optional human-readable description.

        Returns:
            Response from the Omi bridge including send status.
        """
        resp = await self._request("POST", "/api/haptic", json={"pattern": pattern, "message": message})
        log.info("haptic_sent", pattern=pattern, message=message)
        return resp.json()

    async def send_voice_response(self, text: str) -> dict[str, Any]:
        """Send a text-to-speech response through the Omi device.

        Args:
            text: The text to speak through the device.

        Returns:
            Response from the Omi bridge.
        """
        resp = await self._request("POST", "/api/voice/command", json={"text": text})
        log.info("voice_response_sent", text_length=len(text))
        return resp.json()

    async def get_device_status(self) -> dict[str, Any]:
        """Get the current Omi device connection status.

        Returns:
            Dict with ``connected``, ``battery``, ``last_seen``, ``firmware``.
        """
        resp = await self._request("GET", "/api/device/status")
        return resp.json()

    async def execute_voice_command(self, text: str, confirmed: bool = False) -> dict[str, Any]:
        """Execute a voice command by sending text for intent parsing.

        Args:
            text: Natural language command text.
            confirmed: If ``True``, bypass confirmation for destructive commands.

        Returns:
            Command execution result with ``intent``, ``spoken_response``, etc.
        """
        resp = await self._request("POST", "/api/voice/command", json={"text": text, "confirmed": confirmed})
        result = resp.json()
        log.info("voice_command_executed", text=text, intent=result.get("intent"))
        return result

    async def is_connected(self) -> bool:
        """Check if an Omi device is currently connected.

        Returns:
            ``True`` if a device is connected.
        """
        status = await self.get_device_status()
        return status.get("connected", False)
