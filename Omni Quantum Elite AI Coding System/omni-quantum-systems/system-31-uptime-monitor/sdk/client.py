"""
Omni Quantum Elite — Uptime Monitor SDK
Client for Uptime Kuma API integration.
"""

from datetime import datetime, timezone
import httpx


class UptimeClient:
    """Client for Uptime Kuma and webhook relay."""

    def __init__(
        self,
        uptime_kuma_url: str = "http://omni-uptime-kuma:3001",
        webhook_relay_url: str = "http://omni-uptime-webhook-relay:8186",
        timeout: float = 15.0,
    ):
        self.uptime_kuma_url = uptime_kuma_url
        self.webhook_relay_url = webhook_relay_url
        self.timeout = timeout

    def health(self) -> bool:
        """Check Uptime Kuma health."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.uptime_kuma_url}/api/health")
                return resp.status_code == 200
        except Exception:
            return False

    def get_status_page(self, slug: str = "default") -> dict:
        """Get public status page data."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.uptime_kuma_url}/api/status-page/{slug}")
            resp.raise_for_status()
            return resp.json()

    def get_badge(self, monitor_id: int) -> str:
        """Get SVG badge URL for a monitor."""
        return f"{self.uptime_kuma_url}/api/badge/{monitor_id}/status"

    def relay_health(self) -> bool:
        """Check webhook relay health."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.webhook_relay_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
