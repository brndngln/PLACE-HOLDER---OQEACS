"""
System 43 — Mattermost notification helper.

Sends formatted alerts to the configured Mattermost webhook.  All calls
are async so they never block the event loop.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from src.config import settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# -- Emoji map keyed by severity level ----------------------------------------

SEVERITY_EMOJI: dict[str, str] = {
    "critical": ":rotating_light:",
    "high": ":warning:",
    "medium": ":large_orange_diamond:",
    "low": ":information_source:",
    "info": ":white_check_mark:",
    "success": ":tada:",
}


async def send_mattermost_alert(
    title: str,
    message: str,
    severity: str = "info",
    fields: dict[str, Any] | None = None,
) -> bool:
    """Post a formatted alert to the Mattermost incoming-webhook channel.

    Parameters
    ----------
    title:
        Bold header shown at the top of the message.
    message:
        Markdown-formatted body text.
    severity:
        One of ``critical``, ``high``, ``medium``, ``low``, ``info``,
        ``success``.  Controls the emoji prefix.
    fields:
        Optional key/value pairs rendered as a markdown table beneath
        the body.

    Returns
    -------
    bool
        ``True`` when the webhook accepted the payload (HTTP 200),
        ``False`` otherwise (errors are logged, never raised).
    """
    emoji = SEVERITY_EMOJI.get(severity, ":grey_question:")

    # Build the text block
    parts: list[str] = [
        f"{emoji} **[System 43 — Self-Testing] {title}**",
        "",
        message,
    ]

    if fields:
        parts.append("")
        parts.append("| Key | Value |")
        parts.append("|:----|:------|")
        for key, value in fields.items():
            parts.append(f"| {key} | {value} |")

    payload = {"text": "\n".join(parts)}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                settings.MATTERMOST_WEBHOOK_URL,
                json=payload,
            )
            response.raise_for_status()
            logger.info(
                "mattermost_alert_sent",
                title=title,
                severity=severity,
                status=response.status_code,
            )
            return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "mattermost_alert_http_error",
            title=title,
            status=exc.response.status_code,
            body=exc.response.text[:500],
        )
    except httpx.RequestError as exc:
        logger.error(
            "mattermost_alert_request_error",
            title=title,
            error=str(exc),
        )
    return False
