"""Mattermost notification helper — shared across all systems."""
import httpx
import structlog

logger = structlog.get_logger()

EMOJI_MAP = {"critical": "\U0001f534", "warning": "\U0001f7e1", "info": "\U0001f535", "success": "\U0001f7e2"}


async def notify_mattermost(
    webhook_url: str,
    channel: str,
    message: str,
    service_name: str,
    severity: str = "info",
) -> None:
    """Send notification to Mattermost."""
    emoji = EMOJI_MAP.get(severity, "\U0001f535")
    payload = {
        "channel": channel,
        "username": f"omni-{service_name}",
        "icon_emoji": emoji,
        "text": f"{emoji} **[{service_name.upper()}]** {message}",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(webhook_url, json=payload)
    except httpx.HTTPError as exc:
        logger.warning("mattermost_notify_failed", error=str(exc))
