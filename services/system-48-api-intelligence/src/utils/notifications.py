"""Mattermost notification helper for sending alerts and reports."""

from __future__ import annotations

import httpx
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


class MattermostNotifier:
    """Sends formatted notifications to Mattermost via incoming webhooks."""

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._client = http_client
        self._owns_client = http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def send_alert(
        self,
        title: str,
        message: str,
        level: str = "info",
    ) -> bool:
        """Send a formatted alert to the configured Mattermost channel.

        Constructs a Mattermost-compatible webhook payload with color-coded
        attachments based on severity level (critical=red, warning=orange,
        error=red, info=blue).

        Returns True if the message was sent successfully, False otherwise.
        """
        client = await self._get_client()

        color_map = {
            "critical": "#FF0000",
            "error": "#FF0000",
            "warning": "#FFA500",
            "info": "#0066CC",
        }
        color = color_map.get(level, "#0066CC")

        icon_map = {
            "critical": "rotating_light",
            "error": "x",
            "warning": "warning",
            "info": "information_source",
        }
        icon = icon_map.get(level, "information_source")

        payload = {
            "channel": settings.MATTERMOST_CHANNEL,
            "username": "API Intelligence Bot",
            "icon_emoji": icon,
            "attachments": [
                {
                    "fallback": f"[{level.upper()}] {title}: {message}",
                    "color": color,
                    "title": f"[{level.upper()}] {title}",
                    "text": message,
                    "fields": [
                        {
                            "short": True,
                            "title": "Service",
                            "value": settings.SERVICE_NAME,
                        },
                        {
                            "short": True,
                            "title": "Severity",
                            "value": level.upper(),
                        },
                    ],
                }
            ],
        }

        try:
            response = await client.post(
                settings.MATTERMOST_WEBHOOK_URL,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            logger.info(
                "mattermost_alert_sent",
                title=title,
                level=level,
                status=response.status_code,
            )
            return True
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "mattermost_alert_http_error",
                title=title,
                status=exc.response.status_code,
            )
            return False
        except httpx.RequestError as exc:
            logger.warning(
                "mattermost_alert_request_error",
                title=title,
                error=str(exc),
            )
            return False

    async def send_scan_report(
        self,
        total_packages: int,
        outdated: int,
        breaking: int,
        security: int,
    ) -> bool:
        """Send a summary report of a completed dependency scan.

        Formats a clean markdown table of scan statistics and sends it
        to the configured Mattermost channel.
        """
        level = "info"
        if security > 0:
            level = "critical"
        elif breaking > 0:
            level = "warning"

        message = (
            f"| Metric | Count |\n"
            f"|--------|-------|\n"
            f"| Total Packages | {total_packages} |\n"
            f"| Outdated | {outdated} |\n"
            f"| Breaking Changes | {breaking} |\n"
            f"| Security Advisories | {security} |"
        )

        return await self.send_alert(
            title="Dependency Scan Complete",
            message=message,
            level=level,
        )
