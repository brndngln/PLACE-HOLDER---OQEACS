#!/usr/bin/env python3
"""
SYSTEM 26 — CONTAINER MANAGER: Portainer SDK Client
Omni Quantum Elite AI Coding System — Observability Layer

Async Python client for the Portainer REST API. Provides methods for container
management, stack deployment, and resource monitoring. Usable as an async context
manager with built-in retry logic and structured logging.

Requirements: httpx, structlog
"""

import asyncio
from types import TracebackType
from typing import Any, Self

import httpx
import structlog

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
    service="portainer-sdk", system="26", component="container-manager"
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PortainerError(Exception):
    """Raised when a Portainer API call fails."""

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
# Client
# ---------------------------------------------------------------------------


class PortainerClient:
    """Async client for the Portainer REST API.

    Usable as an async context manager::

        async with PortainerClient("http://omni-portainer:9000", "token") as client:
            containers = await client.list_containers()

    Args:
        base_url: Portainer base URL (e.g. http://omni-portainer:9000).
        api_token: JWT token or API key for authentication.
        endpoint_id: Docker endpoint ID (default 1 for local).
        timeout: HTTP request timeout in seconds.
        max_retries: Maximum number of retries on transient errors.
        retry_delay: Base delay between retries in seconds (doubles each attempt).
    """

    def __init__(
        self,
        base_url: str,
        api_token: str,
        endpoint_id: int = 1,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api"
        self.api_token = api_token
        self.endpoint_id = endpoint_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager and close client."""
        await self.close()

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
            path: API path relative to /api.
            **kwargs: Forwarded to httpx request.

        Returns:
            Parsed JSON response, or None for 204 responses.

        Raises:
            PortainerError: On non-retryable HTTP errors.
        """
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

                raise PortainerError(
                    f"Portainer API error: {method} {path} returned {resp.status_code}",
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
                raise PortainerError(
                    f"Connection failed after {self.max_retries} retries: {exc}",
                ) from last_error

        raise PortainerError(
            f"Request failed after {self.max_retries} retries"
        )

    @property
    def _docker(self) -> str:
        """Base path for Docker API calls through Portainer."""
        return f"/endpoints/{self.endpoint_id}/docker"

    # -------------------------------------------------------------------
    # Container Operations
    # -------------------------------------------------------------------

    async def list_containers(
        self, all: bool = True
    ) -> list[dict[str, Any]]:
        """List all containers on the Docker endpoint.

        Args:
            all: Include stopped containers (default True).

        Returns:
            List of container objects with Id, Names, State, Status,
            Image, Ports, and Labels.
        """
        params = {"all": "true" if all else "false"}
        containers = await self._request(
            "GET", f"{self._docker}/containers/json", params=params
        )
        result = containers or []
        log.info("containers_listed", count=len(result), include_stopped=all)
        return result

    async def get_container(self, name: str) -> dict[str, Any]:
        """Get detailed information about a container by name or ID.

        Args:
            name: Container name (e.g. 'omni-loki') or container ID.

        Returns:
            Full container inspect data including config, state, network.

        Raises:
            PortainerError: If the container is not found.
        """
        result = await self._request(
            "GET", f"{self._docker}/containers/{name}/json"
        )
        log.info("container_inspected", container=name)
        return result

    async def restart_container(
        self, name: str, timeout: int = 10
    ) -> None:
        """Restart a container by name or ID.

        Args:
            name: Container name or ID.
            timeout: Seconds to wait before killing (default 10).
        """
        await self._request(
            "POST",
            f"{self._docker}/containers/{name}/restart",
            params={"t": str(timeout)},
        )
        log.info("container_restarted", container=name)

    async def start_container(self, name: str) -> None:
        """Start a stopped container.

        Args:
            name: Container name or ID.
        """
        await self._request(
            "POST", f"{self._docker}/containers/{name}/start"
        )
        log.info("container_started", container=name)

    async def stop_container(
        self, name: str, timeout: int = 10
    ) -> None:
        """Stop a running container.

        Args:
            name: Container name or ID.
            timeout: Seconds to wait before killing.
        """
        await self._request(
            "POST",
            f"{self._docker}/containers/{name}/stop",
            params={"t": str(timeout)},
        )
        log.info("container_stopped", container=name)

    async def get_container_logs(
        self,
        name: str,
        lines: int = 100,
        timestamps: bool = True,
    ) -> str:
        """Get recent logs from a container.

        Args:
            name: Container name or ID.
            lines: Number of log lines to retrieve (default 100).
            timestamps: Include timestamps in output.

        Returns:
            Log output as a string.
        """
        resp = await self._client.get(
            f"{self._docker}/containers/{name}/logs",
            params={
                "stdout": "true",
                "stderr": "true",
                "tail": str(lines),
                "timestamps": "true" if timestamps else "false",
            },
        )
        if resp.status_code >= 400:
            raise PortainerError(
                f"Failed to get logs for {name}",
                status_code=resp.status_code,
                response_body=resp.text,
            )
        log.info(
            "container_logs_fetched", container=name, lines=lines
        )
        return resp.text

    async def get_container_stats(
        self, name: str, stream: bool = False
    ) -> dict[str, Any]:
        """Get resource usage statistics for a container.

        Args:
            name: Container name or ID.
            stream: If False, returns a single stats snapshot.

        Returns:
            Container stats including CPU, memory, network, and block I/O.
        """
        return await self._request(
            "GET",
            f"{self._docker}/containers/{name}/stats",
            params={"stream": "true" if stream else "false"},
        )

    # -------------------------------------------------------------------
    # Stack Operations
    # -------------------------------------------------------------------

    async def list_stacks(self) -> list[dict[str, Any]]:
        """List all stacks managed by Portainer.

        Returns:
            List of stack objects with Id, Name, Status, Type, etc.
        """
        stacks = await self._request("GET", "/stacks")
        result = stacks or []
        log.info("stacks_listed", count=len(result))
        return result

    async def get_stack(self, stack_id: int) -> dict[str, Any]:
        """Get details of a specific stack by ID.

        Args:
            stack_id: Portainer stack ID.

        Returns:
            Stack details including compose content and status.
        """
        return await self._request("GET", f"/stacks/{stack_id}")

    async def deploy_stack(
        self,
        name: str,
        compose_content: str,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Deploy a new stack from a Docker Compose string.

        If a stack with the same name exists, it will be updated instead.

        Args:
            name: Stack name.
            compose_content: Docker Compose YAML as a string.
            env: Environment variables for the stack.

        Returns:
            Created or updated stack object.
        """
        env_list = [
            {"name": k, "value": v} for k, v in (env or {}).items()
        ]

        result = await self._request(
            "POST",
            "/stacks/create/standalone/string",
            params={"endpointId": self.endpoint_id},
            json={
                "Name": name,
                "StackFileContent": compose_content,
                "Env": env_list,
            },
        )
        log.info("stack_deployed", stack=name)
        return result

    async def update_stack(
        self,
        stack_id: int,
        compose_content: str,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Update an existing stack with new compose content.

        Args:
            stack_id: Stack ID.
            compose_content: Updated Docker Compose YAML.
            env: Updated environment variables.

        Returns:
            Updated stack object.
        """
        env_list = [
            {"name": k, "value": v} for k, v in (env or {}).items()
        ]

        result = await self._request(
            "PUT",
            f"/stacks/{stack_id}",
            params={"endpointId": self.endpoint_id},
            json={
                "StackFileContent": compose_content,
                "Env": env_list,
            },
        )
        log.info("stack_updated", stack_id=stack_id)
        return result

    async def remove_stack(self, name: str) -> None:
        """Remove a stack by name.

        Finds the stack by name first, then deletes by ID.

        Args:
            name: Stack name to remove.

        Raises:
            PortainerError: If the stack is not found.
        """
        stacks = await self.list_stacks()
        stack_id = None
        for stack in stacks:
            if stack.get("Name") == name:
                stack_id = stack.get("Id")
                break

        if stack_id is None:
            raise PortainerError(f"Stack '{name}' not found")

        await self._request(
            "DELETE",
            f"/stacks/{stack_id}",
            params={"endpointId": self.endpoint_id},
        )
        log.info("stack_removed", stack=name, stack_id=stack_id)

    # -------------------------------------------------------------------
    # Resource Monitoring
    # -------------------------------------------------------------------

    async def get_resource_usage(self) -> dict[str, Any]:
        """Get aggregated resource usage across all running containers.

        Fetches stats for each running container and computes CPU%,
        memory usage/limit, and network I/O. Generates alerts for
        containers exceeding 90% RAM or CPU.

        Returns:
            Dictionary with per-container stats, alerts, and summary.
        """
        containers = await self.list_containers(all=False)
        usage: dict[str, Any] = {
            "containers": [],
            "summary": {
                "total_containers": len(containers),
                "total_memory_usage_mb": 0.0,
                "total_memory_limit_mb": 0.0,
            },
        }

        for container in containers:
            name = (
                container.get("Names", ["/unknown"])[0]
            ).lstrip("/")
            cid = container.get("Id", "")

            try:
                stats = await self.get_container_stats(cid)
            except PortainerError:
                log.warning(
                    "stats_fetch_failed", container=name
                )
                continue

            # Parse memory stats
            mem_stats = stats.get("memory_stats", {})
            mem_usage = mem_stats.get("usage", 0)
            mem_limit = mem_stats.get("limit", 0)
            mem_usage_mb = mem_usage / (1024 * 1024)
            mem_limit_mb = mem_limit / (1024 * 1024)
            mem_pct = (
                (mem_usage / mem_limit * 100) if mem_limit > 0 else 0
            )

            # Parse CPU stats
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})
            cpu_delta = cpu_stats.get("cpu_usage", {}).get(
                "total_usage", 0
            ) - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            system_delta = cpu_stats.get(
                "system_cpu_usage", 0
            ) - precpu_stats.get("system_cpu_usage", 0)
            cpu_count = cpu_stats.get("online_cpus", 1)
            cpu_pct = (
                (cpu_delta / system_delta * cpu_count * 100)
                if system_delta > 0
                else 0
            )

            # Parse network stats
            networks = stats.get("networks", {})
            net_rx = sum(
                v.get("rx_bytes", 0) for v in networks.values()
            )
            net_tx = sum(
                v.get("tx_bytes", 0) for v in networks.values()
            )

            container_usage: dict[str, Any] = {
                "name": name,
                "id": cid[:12],
                "state": container.get("State", ""),
                "cpu_percent": round(cpu_pct, 2),
                "memory_usage_mb": round(mem_usage_mb, 2),
                "memory_limit_mb": round(mem_limit_mb, 2),
                "memory_percent": round(mem_pct, 2),
                "network_rx_mb": round(net_rx / (1024 * 1024), 2),
                "network_tx_mb": round(net_tx / (1024 * 1024), 2),
                "alerts": [],
            }

            if mem_pct > 90:
                alert = f"HIGH MEMORY: {name} using {mem_pct:.1f}% of allocated RAM"
                container_usage["alerts"].append(alert)
                log.warning("resource_alert", alert=alert)
            if cpu_pct > 90:
                alert = f"HIGH CPU: {name} using {cpu_pct:.1f}% of allocated CPU"
                container_usage["alerts"].append(alert)
                log.warning("resource_alert", alert=alert)

            usage["containers"].append(container_usage)
            usage["summary"]["total_memory_usage_mb"] += mem_usage_mb
            usage["summary"]["total_memory_limit_mb"] += mem_limit_mb

        usage["summary"]["total_memory_usage_mb"] = round(
            usage["summary"]["total_memory_usage_mb"], 2
        )
        usage["summary"]["total_memory_limit_mb"] = round(
            usage["summary"]["total_memory_limit_mb"], 2
        )

        all_alerts: list[str] = []
        for c in usage["containers"]:
            all_alerts.extend(c["alerts"])
        usage["summary"]["alerts"] = all_alerts
        usage["summary"]["alert_count"] = len(all_alerts)

        log.info(
            "resource_usage_computed",
            containers=len(usage["containers"]),
            alerts=len(all_alerts),
        )
        return usage

    # -------------------------------------------------------------------
    # Endpoint & System Info
    # -------------------------------------------------------------------

    async def get_system_status(self) -> dict[str, Any]:
        """Get Portainer system status.

        Returns:
            System status including version and instance ID.
        """
        return await self._request("GET", "/system/status")

    async def get_endpoint_info(self) -> dict[str, Any]:
        """Get Docker endpoint info (version, OS, architecture, etc).

        Returns:
            Docker engine info dictionary.
        """
        return await self._request("GET", f"{self._docker}/info")

    async def get_docker_version(self) -> dict[str, Any]:
        """Get Docker engine version info.

        Returns:
            Docker version details including API version.
        """
        return await self._request("GET", f"{self._docker}/version")
