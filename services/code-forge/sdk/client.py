#!/usr/bin/env python3
"""
SYSTEM 36 — CODE FORGE: Coder SDK Client
Omni Quantum Elite AI Coding System — Dev Environments

Async client for the Coder REST API v2. Provides workspace lifecycle
management, template listing, and resource inspection. Typed Pydantic
returns, httpx transport, and structured logging via structlog.

Requirements: httpx, structlog, pydantic
"""

import asyncio
from datetime import datetime
from enum import Enum
from types import TracebackType
from typing import Any, Self

import httpx
import structlog
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Structured Logging
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

log = structlog.get_logger(
    service="coder-sdk", system="36", component="code-forge"
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CoderError(Exception):
    """Raised when a Coder API call fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str = "",
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class WorkspaceStatus(str, Enum):
    """Workspace lifecycle status."""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    CANCELING = "canceling"
    CANCELED = "canceled"
    DELETING = "deleting"
    DELETED = "deleted"


class WorkspaceAgent(BaseModel):
    """A running agent inside a workspace."""
    id: str = ""
    name: str = ""
    status: str = ""
    architecture: str = ""
    operating_system: str = ""
    startup_script_behavior: str = ""
    directory: str = ""
    first_connected_at: str | None = None
    last_connected_at: str | None = None
    latency_ms: float = 0


class WorkspaceResource(BaseModel):
    """A provisioned resource within a workspace."""
    id: str = ""
    name: str = ""
    type: str = ""
    agents: list[WorkspaceAgent] = Field(default_factory=list)
    metadata: list[dict[str, Any]] = Field(default_factory=list)
    daily_cost: int = 0


class WorkspaceBuild(BaseModel):
    """A workspace build (provision) record."""
    id: str = ""
    build_number: int = 0
    transition: str = ""
    status: str = ""
    template_version_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    resources: list[WorkspaceResource] = Field(default_factory=list)


class Workspace(BaseModel):
    """A Coder workspace with full metadata."""
    id: str = ""
    name: str = ""
    owner_id: str = ""
    owner_name: str = ""
    template_id: str = ""
    template_name: str = ""
    template_display_name: str = ""
    latest_build: WorkspaceBuild | None = None
    created_at: str = ""
    updated_at: str = ""
    last_used_at: str = ""
    outdated: bool = False
    autostart_schedule: str | None = None
    ttl_ms: int | None = None
    health: str = ""

    @property
    def status(self) -> str:
        """Derive current status from the latest build."""
        if self.latest_build:
            return self.latest_build.status
        return "unknown"


class WorkspaceResources(BaseModel):
    """Aggregated resources for a workspace."""
    workspace_id: str = ""
    workspace_name: str = ""
    resources: list[WorkspaceResource] = Field(default_factory=list)
    agents: list[WorkspaceAgent] = Field(default_factory=list)


class TemplateVersion(BaseModel):
    """A template version snapshot."""
    id: str = ""
    template_id: str = ""
    name: str = ""
    created_at: str = ""
    created_by_id: str = ""
    created_by_name: str = ""


class Template(BaseModel):
    """A Coder workspace template."""
    id: str = ""
    name: str = ""
    display_name: str = ""
    description: str = ""
    organization_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    active_version_id: str = ""
    active_user_count: int = 0
    build_time_stats: dict[str, Any] = Field(default_factory=dict)
    default_ttl_ms: int = 0
    max_ttl_ms: int = 0


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class CoderClient:
    """Async client for the Coder REST API v2.

    Usable as an async context manager with built-in retry logic and
    structured logging::

        async with CoderClient("http://omni-coder:7080", "token-xxx") as coder:
            workspaces = await coder.list_workspaces()
            ws = await coder.create_workspace("python-dev", "my-workspace")
            await coder.stop_workspace("my-workspace")

    Args:
        base_url: Coder server base URL (e.g. http://omni-coder:7080).
        api_token: Coder session token or API key.
        timeout: HTTP request timeout in seconds.
        max_retries: Maximum retries on transient errors.
        retry_delay: Base delay between retries in seconds (doubles each attempt).
    """

    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v2"
        self.api_token = api_token
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def __aenter__(self) -> Self:
        """Enter async context manager and open the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={
                "Coder-Session-Token": self.api_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=self._timeout,
        )
        log.info("coder_client_opened", base_url=self.base_url)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager and close the HTTP client."""
        if self._client:
            await self._client.aclose()
            log.info("coder_client_closed")

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()

    # -------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> Any:
        """Make an authenticated API request with retry logic.

        Retries on 5xx errors and connection failures up to ``max_retries``
        times with exponential backoff.

        Args:
            method: HTTP method.
            path: API path relative to /api/v2.
            **kwargs: Forwarded to httpx request.

        Returns:
            Parsed JSON response, or None for 204 responses.

        Raises:
            CoderError: On non-retryable HTTP errors.
        """
        assert self._client is not None, "Client not opened — use 'async with'"
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self._client.request(method, path, **kwargs)

                if resp.status_code < 400:
                    if resp.status_code == 204 or not resp.content:
                        return None
                    return resp.json()

                if resp.status_code >= 500 and attempt < self.max_retries:
                    log.warning(
                        "retrying_request",
                        method=method,
                        path=path,
                        status=resp.status_code,
                        attempt=attempt,
                    )
                    await asyncio.sleep(
                        self.retry_delay * (2 ** (attempt - 1))
                    )
                    continue

                raise CoderError(
                    f"Coder API error: {method} {path} returned {resp.status_code}",
                    status_code=resp.status_code,
                    response_body=resp.text,
                )

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    log.warning(
                        "retrying_connection",
                        method=method,
                        path=path,
                        error=str(exc),
                        attempt=attempt,
                    )
                    await asyncio.sleep(
                        self.retry_delay * (2 ** (attempt - 1))
                    )
                    continue
                raise CoderError(
                    f"Connection failed after {self.max_retries} retries: {exc}",
                ) from last_error

        raise CoderError(
            f"Request failed after {self.max_retries} retries"
        )

    def _parse_workspace(self, data: dict[str, Any]) -> Workspace:
        """Parse a raw API workspace dict into a Workspace model."""
        build_data = data.get("latest_build")
        latest_build = None
        if build_data:
            resources = []
            for res in build_data.get("resources", []):
                agents = [
                    WorkspaceAgent(**a) for a in res.get("agents", [])
                ]
                resources.append(WorkspaceResource(
                    id=res.get("id", ""),
                    name=res.get("name", ""),
                    type=res.get("type", ""),
                    agents=agents,
                    metadata=res.get("metadata", []),
                    daily_cost=res.get("daily_cost", 0),
                ))
            latest_build = WorkspaceBuild(
                id=build_data.get("id", ""),
                build_number=build_data.get("build_number", 0),
                transition=build_data.get("transition", ""),
                status=build_data.get("status", ""),
                template_version_id=build_data.get("template_version_id", ""),
                created_at=build_data.get("created_at", ""),
                updated_at=build_data.get("updated_at", ""),
                resources=resources,
            )

        return Workspace(
            id=data.get("id", ""),
            name=data.get("name", ""),
            owner_id=data.get("owner_id", ""),
            owner_name=data.get("owner_name", ""),
            template_id=data.get("template_id", ""),
            template_name=data.get("template_name", ""),
            template_display_name=data.get("template_display_name", ""),
            latest_build=latest_build,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            last_used_at=data.get("last_used_at", ""),
            outdated=data.get("outdated", False),
            autostart_schedule=data.get("autostart_schedule"),
            ttl_ms=data.get("ttl_ms"),
            health=data.get("health", {}).get("overall", "") if isinstance(data.get("health"), dict) else str(data.get("health", "")),
        )

    # -------------------------------------------------------------------
    # Workspace Operations
    # -------------------------------------------------------------------

    async def list_workspaces(
        self,
        owner: str = "me",
        search: str | None = None,
    ) -> list[Workspace]:
        """List all workspaces accessible to the authenticated user.

        Args:
            owner: Filter by owner (default "me" for current user).
                   Use "" for all workspaces visible to the user.
            search: Optional search query string.

        Returns:
            List of Workspace objects.
        """
        params: dict[str, str] = {}
        query_parts: list[str] = []
        if owner:
            query_parts.append(f"owner:{owner}")
        if search:
            query_parts.append(search)
        if query_parts:
            params["q"] = " ".join(query_parts)

        data = await self._request("GET", "/workspaces", params=params)
        workspaces_data = data.get("workspaces", []) if data else []

        result = [self._parse_workspace(w) for w in workspaces_data]
        log.info("workspaces_listed", count=len(result), owner=owner)
        return result

    async def create_workspace(
        self,
        template: str,
        name: str,
        parameters: dict[str, str] | None = None,
        autostart_schedule: str | None = None,
        ttl_ms: int | None = None,
    ) -> Workspace:
        """Create a new workspace from a template.

        Args:
            template: Template name (e.g. "python-dev").
            name: Workspace name (must be unique per user).
            parameters: Template parameter overrides (e.g. {"python_version": "3.12"}).
            autostart_schedule: Cron schedule for auto-start (optional).
            ttl_ms: Time to live in milliseconds (optional, default from template).

        Returns:
            Created Workspace object.

        Raises:
            CoderError: If the template is not found or creation fails.
        """
        # Resolve template name to template ID
        templates = await self.list_templates()
        template_obj = None
        for t in templates:
            if t.name == template:
                template_obj = t
                break

        if not template_obj:
            raise CoderError(f"Template not found: {template}")

        # Build rich parameter values
        rich_parameter_values: list[dict[str, str]] = []
        if parameters:
            for param_name, param_value in parameters.items():
                rich_parameter_values.append({
                    "name": param_name,
                    "value": param_value,
                })

        payload: dict[str, Any] = {
            "name": name,
            "template_id": template_obj.id,
            "rich_parameter_values": rich_parameter_values,
        }

        if autostart_schedule:
            payload["autostart_schedule"] = autostart_schedule
        if ttl_ms is not None:
            payload["ttl_ms"] = ttl_ms

        data = await self._request(
            "POST", "/organizations/me/workspaces", json=payload
        )

        workspace = self._parse_workspace(data)
        log.info(
            "workspace_created",
            workspace=name,
            template=template,
            workspace_id=workspace.id,
        )
        return workspace

    async def _get_workspace_raw(self, name: str) -> dict[str, Any]:
        """Get raw workspace data by name for the current user.

        Args:
            name: Workspace name.

        Returns:
            Raw workspace dict from API.

        Raises:
            CoderError: If the workspace is not found.
        """
        data = await self._request("GET", f"/users/me/workspace/{name}")
        if not data:
            raise CoderError(f"Workspace not found: {name}")
        return data

    async def _build_workspace(
        self, workspace_id: str, transition: str
    ) -> dict[str, Any]:
        """Trigger a workspace build transition.

        Args:
            workspace_id: Workspace UUID.
            transition: One of "start", "stop", "delete".

        Returns:
            Build response dict.
        """
        payload = {"transition": transition}
        return await self._request(
            "POST",
            f"/workspaces/{workspace_id}/builds",
            json=payload,
        )

    async def start_workspace(self, name: str) -> Workspace:
        """Start a stopped workspace.

        Args:
            name: Workspace name.

        Returns:
            Updated Workspace object.
        """
        raw = await self._get_workspace_raw(name)
        workspace_id = raw.get("id", "")

        await self._build_workspace(workspace_id, "start")
        log.info("workspace_started", workspace=name, workspace_id=workspace_id)

        # Fetch updated workspace
        updated = await self._get_workspace_raw(name)
        return self._parse_workspace(updated)

    async def stop_workspace(self, name: str) -> Workspace:
        """Stop a running workspace.

        Args:
            name: Workspace name.

        Returns:
            Updated Workspace object.
        """
        raw = await self._get_workspace_raw(name)
        workspace_id = raw.get("id", "")

        await self._build_workspace(workspace_id, "stop")
        log.info("workspace_stopped", workspace=name, workspace_id=workspace_id)

        # Fetch updated workspace
        updated = await self._get_workspace_raw(name)
        return self._parse_workspace(updated)

    async def delete_workspace(self, name: str) -> bool:
        """Delete a workspace permanently.

        Args:
            name: Workspace name.

        Returns:
            True if the workspace was deleted successfully.

        Raises:
            CoderError: If the workspace is not found or deletion fails.
        """
        raw = await self._get_workspace_raw(name)
        workspace_id = raw.get("id", "")

        await self._build_workspace(workspace_id, "delete")
        log.info("workspace_deleted", workspace=name, workspace_id=workspace_id)
        return True

    async def get_workspace_resources(self, name: str) -> WorkspaceResources:
        """Get all provisioned resources and agents for a workspace.

        Args:
            name: Workspace name.

        Returns:
            WorkspaceResources with all resource and agent details.
        """
        raw = await self._get_workspace_raw(name)
        workspace = self._parse_workspace(raw)

        all_resources: list[WorkspaceResource] = []
        all_agents: list[WorkspaceAgent] = []

        if workspace.latest_build:
            for resource in workspace.latest_build.resources:
                all_resources.append(resource)
                all_agents.extend(resource.agents)

        result = WorkspaceResources(
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            resources=all_resources,
            agents=all_agents,
        )

        log.info(
            "workspace_resources_fetched",
            workspace=name,
            resource_count=len(all_resources),
            agent_count=len(all_agents),
        )
        return result

    # -------------------------------------------------------------------
    # Template Operations
    # -------------------------------------------------------------------

    async def list_templates(
        self, organization: str = "me"
    ) -> list[Template]:
        """List all available workspace templates.

        Args:
            organization: Organization slug (default "me" for the user's org).

        Returns:
            List of Template objects.
        """
        data = await self._request(
            "GET", f"/organizations/{organization}/templates"
        )

        templates_data = data if isinstance(data, list) else []
        result: list[Template] = []
        for t in templates_data:
            result.append(Template(
                id=t.get("id", ""),
                name=t.get("name", ""),
                display_name=t.get("display_name", ""),
                description=t.get("description", ""),
                organization_id=t.get("organization_id", ""),
                created_at=t.get("created_at", ""),
                updated_at=t.get("updated_at", ""),
                active_version_id=t.get("active_version_id", ""),
                active_user_count=t.get("active_user_count", 0),
                build_time_stats=t.get("build_time_stats", {}),
                default_ttl_ms=t.get("default_ttl_ms", 0),
                max_ttl_ms=t.get("max_ttl_ms", 0),
            ))

        log.info("templates_listed", count=len(result), organization=organization)
        return result

    # -------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------

    async def health_check(self) -> dict[str, bool]:
        """Check Coder server health status.

        Returns:
            Dictionary with healthy, derp, access_url, websocket,
            database, and provisioner_daemons status.
        """
        assert self._client is not None, "Client not opened — use 'async with'"
        result: dict[str, bool] = {
            "healthy": False,
            "database": False,
            "provisioner_daemons": False,
        }

        try:
            resp = await self._client.get(f"{self.base_url}/healthz")
            result["healthy"] = resp.status_code == 200
        except Exception:
            pass

        try:
            data = await self._request("GET", "/debug/health")
            if data:
                result["healthy"] = data.get("healthy", False)
                result["database"] = data.get("database", {}).get("healthy", False)
                result["provisioner_daemons"] = data.get("provisioner_daemons", {}).get("healthy", False)
        except (CoderError, Exception):
            pass

        log.info("health_check", **result)
        return result
