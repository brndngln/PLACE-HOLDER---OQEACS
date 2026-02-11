#!/usr/bin/env python3
"""
SYSTEM 10 — COMMUNICATION HUB: Mattermost SDK Client
Omni Quantum Elite AI Coding System — Communication & Workflow Layer

Async Python client for the Mattermost REST API.  Provides convenience
methods for posting formatted messages, managing alerts, and reading
channel history.

Requirements: httpx, structlog
"""

import asyncio
from types import TracebackType
from typing import Any, Self

import httpx
import structlog

log = structlog.get_logger(service="mattermost-client", system="10", component="communication-hub")


class MattermostClient:
    """Async Mattermost REST API client with retry logic and structured logging.

    Usage::

        async with MattermostClient("http://omni-mattermost:8065", bot_token) as mm:
            await mm.post_message("omni-alerts", "Something happened")
    """

    def __init__(
        self,
        base_url: str,
        bot_token: str,
        *,
        team_name: str = "omni-quantum",
        max_retries: int = 3,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.bot_token = bot_token
        self.team_name = team_name
        self.max_retries = max_retries
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._team_id: str | None = None
        self._channel_cache: dict[str, str] = {}

    # -- Async context manager -------------------------------------------------

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            base_url=f"{self.base_url}/api/v4",
            headers={
                "Authorization": f"Bearer {self.bot_token}",
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

    # -- Internal helpers ------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Issue an HTTP request with exponential-backoff retry on transient errors."""
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

    async def _get_team_id(self) -> str:
        """Resolve and cache the team ID."""
        if self._team_id is None:
            resp = await self._request("GET", f"/teams/name/{self.team_name}")
            self._team_id = resp.json()["id"]
        return self._team_id

    async def _resolve_channel(self, channel_name: str) -> str:
        """Resolve channel name → ID, caching results."""
        if channel_name not in self._channel_cache:
            team_id = await self._get_team_id()
            resp = await self._request("GET", f"/teams/{team_id}/channels/name/{channel_name}")
            self._channel_cache[channel_name] = resp.json()["id"]
        return self._channel_cache[channel_name]

    # -- Public API ------------------------------------------------------------

    async def post_message(
        self,
        channel: str,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Post a text message (optionally with attachments) to a channel.

        Args:
            channel: Channel name (e.g. ``"omni-alerts"``).
            text: Markdown message body.
            attachments: Optional Mattermost attachment objects.

        Returns:
            The created post object.
        """
        channel_id = await self._resolve_channel(channel)
        payload: dict[str, Any] = {"channel_id": channel_id, "message": text}
        if attachments:
            payload["props"] = {"attachments": attachments}
        resp = await self._request("POST", "/posts", json=payload)
        log.info("message_posted", channel=channel, length=len(text))
        return resp.json()

    async def post_alert(
        self,
        channel: str,
        title: str,
        message: str,
        severity: str,
        source: str,
    ) -> dict[str, Any]:
        """Post a color-coded alert attachment.

        Args:
            channel: Target channel name.
            title: Alert title.
            message: Alert description body.
            severity: One of ``critical``, ``warning``, ``info``, ``resolved``.
            source: Originating system name.

        Returns:
            The created post object.
        """
        color_map = {"critical": "#FF0000", "warning": "#FFA500", "info": "#36A64F", "resolved": "#00FF00"}
        attachment = {
            "color": color_map.get(severity, "#808080"),
            "title": title,
            "text": message,
            "fields": [
                {"short": True, "title": "Severity", "value": severity.upper()},
                {"short": True, "title": "Source", "value": source},
            ],
            "footer": "Omni Quantum Alert System",
        }
        mention = "@channel " if severity == "critical" else ""
        return await self.post_message(channel, f"{mention}{title}", [attachment])

    async def post_build_status(
        self,
        repo: str,
        branch: str,
        status: str,
        duration: str,
        url: str,
    ) -> dict[str, Any]:
        """Post a build status notification to ``#builds``.

        Args:
            repo: Repository full name.
            branch: Git branch.
            status: Build result (``success``, ``failure``, ``running``).
            duration: Human-readable duration.
            url: Link to CI pipeline.

        Returns:
            The created post object.
        """
        color = {"success": "#36A64F", "failure": "#FF0000", "running": "#FFA500"}.get(status, "#808080")
        emoji = {"success": ":white_check_mark:", "failure": ":x:", "running": ":hourglass:"}.get(status, ":grey_question:")
        attachment = {
            "color": color,
            "title": f"{emoji} Build {status.upper()} — {repo}",
            "title_link": url,
            "fields": [
                {"short": True, "title": "Branch", "value": f"`{branch}`"},
                {"short": True, "title": "Duration", "value": duration},
            ],
            "footer": "Woodpecker CI",
        }
        return await self.post_message("omni-builds", "", [attachment])

    async def post_review_score(
        self,
        task_id: str,
        score: float,
        dimensions: dict[str, float],
        passed: bool,
    ) -> dict[str, Any]:
        """Post a code review quality score to ``#reviews``.

        Args:
            task_id: Unique task/PR identifier.
            score: Overall quality score 0-10.
            dimensions: Per-dimension scores.
            passed: Whether the quality gate passed.

        Returns:
            The created post object.
        """
        gate = "PASSED :white_check_mark:" if passed else "FAILED :x:"
        color = "#36A64F" if score >= 7 else "#FFA500" if score >= 5 else "#FF0000"
        fields = [
            {"short": True, "title": "Quality Score", "value": f"**{score}/10**"},
            {"short": True, "title": "Gate", "value": gate},
        ]
        for dim_name, dim_val in dimensions.items():
            fields.append({"short": True, "title": dim_name.replace("_", " ").title(), "value": f"{dim_val}/10"})
        attachment = {"color": color, "title": f"Code Review — {task_id}", "fields": fields, "footer": "Code Scorer + Gate Engine"}
        return await self.post_message("omni-reviews", "", [attachment])

    async def create_incident(
        self,
        title: str,
        severity: str,
        affected_services: list[str],
    ) -> dict[str, Any]:
        """Create an incident post in ``#incidents``.

        Args:
            title: Incident title.
            severity: Severity level.
            affected_services: List of affected service names.

        Returns:
            The created post object.
        """
        color = "#FF0000" if severity == "critical" else "#FFA500"
        attachment = {
            "color": color,
            "title": f":rotating_light: INCIDENT: {title}",
            "fields": [
                {"short": True, "title": "Severity", "value": severity.upper()},
                {"short": False, "title": "Affected Services", "value": ", ".join(affected_services)},
            ],
            "footer": "Omni Quantum Incident Management",
        }
        return await self.post_message("omni-incidents", f"@channel New incident: **{title}**", [attachment])

    async def resolve_incident(
        self,
        incident_id: str,
        resolution: str,
    ) -> dict[str, Any]:
        """Post an incident resolution to ``#incidents``.

        Args:
            incident_id: Original incident identifier or post ID.
            resolution: Description of the resolution.

        Returns:
            The created post object.
        """
        attachment = {
            "color": "#00FF00",
            "title": ":white_check_mark: INCIDENT RESOLVED",
            "fields": [
                {"short": True, "title": "Incident", "value": incident_id},
                {"short": False, "title": "Resolution", "value": resolution},
            ],
            "footer": "Omni Quantum Incident Management",
        }
        return await self.post_message("omni-incidents", f"Incident **{incident_id}** resolved", [attachment])

    async def get_channel_history(
        self,
        channel: str,
        count: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve recent posts from a channel.

        Args:
            channel: Channel name.
            count: Number of posts to retrieve (max 200).

        Returns:
            List of post objects ordered newest-first.
        """
        channel_id = await self._resolve_channel(channel)
        resp = await self._request("GET", f"/channels/{channel_id}/posts", params={"per_page": min(count, 200)})
        data = resp.json()
        order = data.get("order", [])
        posts = data.get("posts", {})
        return [posts[pid] for pid in order if pid in posts]
