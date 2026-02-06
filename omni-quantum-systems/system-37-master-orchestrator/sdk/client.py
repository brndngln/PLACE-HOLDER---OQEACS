"""
Omni Quantum Elite — Master Orchestrator SDK
=============================================
Unified Python client for controlling all 36 platform systems.

Usage:
    from sdk.client import OmniClient

    omni = OmniClient()
    print(omni.status())
    print(omni.health("vault"))
    omni.restart("gitea")
    omni.backup("postgresql")
"""

import httpx
from typing import Any


class OmniClient:
    """Unified client for the Omni Quantum Elite platform."""

    def __init__(
        self,
        url: str = "http://omni-orchestrator:9500",
        timeout: float = 15.0,
    ):
        self.url = url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> dict:
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.get(f"{self.url}{path}")
            resp.raise_for_status()
            return resp.json()

    def _post(self, path: str, data: dict | None = None) -> dict:
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.post(f"{self.url}{path}", json=data or {})
            resp.raise_for_status()
            return resp.json()

    # ---- Status ----

    def health(self, service: str | None = None) -> dict:
        """Check health of a specific service or the orchestrator itself."""
        if service:
            return self._get(f"/api/v1/status/name/{service}")
        return self._get("/health")

    def status(self, tier: str | None = None, tag: str | None = None) -> dict:
        """Get status of all services, optionally filtered."""
        params = []
        if tier:
            params.append(f"tier={tier}")
        if tag:
            params.append(f"tag={tag}")
        qs = f"?{'&'.join(params)}" if params else ""
        return self._get(f"/api/v1/status{qs}")

    def overview(self) -> dict:
        """Executive summary of platform health."""
        return self._get("/api/v1/overview")

    def service_up(self, service: str) -> bool:
        """Quick check if a service is healthy."""
        try:
            data = self.health(service)
            return data.get("status") == "healthy"
        except Exception:
            return False

    def all_healthy(self) -> bool:
        """Check if all services are healthy."""
        data = self.overview()
        return data.get("down", 1) == 0 and data.get("degraded", 1) == 0

    # ---- Actions ----

    def restart(self, service: str) -> dict:
        """Restart a service container."""
        return self._post("/api/v1/action/restart", {"target": service})

    def backup(self, service: str = "all") -> dict:
        """Trigger backup for a service or all."""
        return self._post("/api/v1/action/backup", {"target": service})

    def deploy(self, app: str) -> dict:
        """Trigger deployment."""
        return self._post("/api/v1/action/deploy", {"target": app})

    def rotate_secrets(self, service: str = "all") -> dict:
        """Trigger secret rotation."""
        return self._post("/api/v1/action/rotate-secrets", {"target": service})

    def refresh(self) -> dict:
        """Force refresh health checks."""
        return self._post("/api/v1/action/refresh")

    # ---- Discovery ----

    def search(self, query: str) -> list[dict]:
        """Search services by name, tag, or description."""
        data = self._get(f"/api/v1/search?q={query}")
        return data.get("results", [])

    def topology(self) -> dict:
        """Get service dependency graph."""
        return self._get("/api/v1/topology")

    def registry(self) -> dict:
        """Full service registry metadata."""
        return self._get("/api/v1/registry")

    # ---- Events ----

    def events(self, limit: int = 50) -> list[dict]:
        """Recent platform events."""
        data = self._get(f"/api/v1/events/history?limit={limit}")
        return data.get("events", [])

    # ---- Docker ----

    def docker_stats(self) -> dict:
        """Docker host resource info."""
        return self._get("/api/v1/docker/stats")

    def containers(self) -> list[dict]:
        """List omni quantum Docker containers."""
        data = self._get("/api/v1/docker/containers")
        return data.get("containers", [])

    # ---- Voice ----

    def voice_command(self, transcript: str, voice_url: str = "http://omni-voice-bridge:9502") -> dict:
        """Send a voice command transcript."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.post(f"{voice_url}/voice/command", json={"transcript": transcript})
            resp.raise_for_status()
            return resp.json()

    # ---- Convenience ----

    def platform_report(self) -> str:
        """Generate a human-readable platform report."""
        ov = self.overview()
        status_data = self.status()
        services = status_data.get("services", [])
        docker = self.docker_stats()

        lines = [
            f"╔══════════════════════════════════════════╗",
            f"║   ⚛ Omni Quantum Elite — Platform Report ║",
            f"╚══════════════════════════════════════════╝",
            f"",
            f"  Status:    {ov.get('emoji', '')} {ov.get('platform_status', 'unknown').upper()}",
            f"  Healthy:   {ov.get('healthy', 0)}/{ov.get('total_services', 36)}",
            f"  Uptime:    {ov.get('uptime_pct', 0)}%",
            f"  Docker:    {docker.get('containers_running', 0)} running on {docker.get('cpu_count', 0)} CPUs / {docker.get('memory_gb', 0)} GB",
            f"",
        ]

        down_services = [s for s in services if s.get("status") == "down"]
        if down_services:
            lines.append("  ⚠ DOWN SERVICES:")
            for s in down_services:
                lines.append(f"    🔴 #{s['id']} {s['name']} — {s.get('message', '')}")
            lines.append("")

        degraded_services = [s for s in services if s.get("status") == "degraded"]
        if degraded_services:
            lines.append("  ⚠ DEGRADED SERVICES:")
            for s in degraded_services:
                lines.append(f"    🟡 #{s['id']} {s['name']} — {s.get('message', '')}")
            lines.append("")

        return "\n".join(lines)
