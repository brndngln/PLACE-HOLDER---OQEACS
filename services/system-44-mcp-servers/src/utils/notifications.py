"""
System 44 — Mattermost webhook notification helper.

Sends structured notifications to a Mattermost channel via incoming
webhook.  Failures are logged and silently swallowed so that
notification issues never crash the calling server.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from src.config import settings

logger: structlog.stdlib.BoundLogger = structlog.get_logger("system44.notifications")

_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)


async def notify_mattermost(
    text: str,
    *,
    channel: str | None = None,
    username: str = "System 44 MCP",
    icon_url: str | None = None,
    fields: list[dict[str, Any]] | None = None,
) -> bool:
    """Post a message to Mattermost via incoming webhook.

    Parameters
    ----------
    text:
        Markdown-formatted message body.
    channel:
        Override the webhook's default channel (optional).
    username:
        Display name for the bot post.
    icon_url:
        Avatar URL for the bot post (optional).
    fields:
        Optional attachment fields for richer formatting.

    Returns
    -------
    bool
        ``True`` if the webhook accepted the payload, ``False`` otherwise.
    """
    webhook_url = settings.MATTERMOST_WEBHOOK_URL

    payload: dict[str, Any] = {
        "username": username,
        "text": text,
    }
    if channel:
        payload["channel"] = channel
    if icon_url:
        payload["icon_url"] = icon_url
    if fields:
        payload["attachments"] = [
            {
                "fields": fields,
            }
        ]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code == 200:
                logger.info(
                    "mattermost_notification_sent",
                    text_preview=text[:80],
                )
                return True
            logger.warning(
                "mattermost_notification_rejected",
                status=response.status_code,
                body=response.text[:200],
            )
            return False
    except httpx.HTTPError as exc:
        logger.warning(
            "mattermost_notification_failed",
            error=str(exc),
        )
        return False
    except Exception as exc:
        logger.warning(
            "mattermost_notification_unexpected_error",
            error=str(exc),
        )
        return False


async def notify_tool_error(
    server_name: str,
    tool_name: str,
    error: str,
) -> bool:
    """Send a formatted error notification for a failed tool invocation."""
    text = (
        f"**:warning: MCP Tool Error**\n"
        f"**Server:** {server_name}\n"
        f"**Tool:** `{tool_name}`\n"
        f"**Error:** {error}"
    )
    return await notify_mattermost(text, username=f"MCP {server_name}")


async def notify_deploy_event(
    project_id: str,
    environment: str,
    status: str,
    url: str | None = None,
) -> bool:
    """Send a deployment-specific notification."""
    status_emoji = {
        "success": ":white_check_mark:",
        "failed": ":x:",
        "rolled_back": ":rewind:",
        "in_progress": ":hourglass:",
    }.get(status, ":information_source:")

    text = (
        f"**{status_emoji} Deployment Update**\n"
        f"**Project:** `{project_id}`\n"
        f"**Environment:** {environment}\n"
        f"**Status:** {status}"
    )
    if url:
        text += f"\n**URL:** {url}"

    return await notify_mattermost(text, username="MCP Deploy")
