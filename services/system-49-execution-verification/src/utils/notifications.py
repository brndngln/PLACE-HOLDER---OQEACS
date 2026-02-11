"""Mattermost notification helper."""

from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger()


async def send_mattermost_notification(
    webhook_url: str,
    text: str,
    *,
    username: str = "Execution Verifier",
    icon_url: str = "",
) -> bool:
    """Post a message to Mattermost via incoming webhook.

    Returns True on success, False on failure.
    """
    if not webhook_url:
        logger.debug("mattermost_skip", reason="no webhook URL configured")
        return False

    payload: dict = {"text": text, "username": username}
    if icon_url:
        payload["icon_url"] = icon_url

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        logger.info("mattermost_sent", status=resp.status_code)
        return True
    except Exception as exc:
        logger.warning("mattermost_failed", error=str(exc))
        return False


async def notify_verification_result(
    webhook_url: str,
    result_id: str,
    language: str,
    status: str,
    attempts: int,
) -> bool:
    """Send a formatted verification-result notification."""
    status_emoji = {"verified": ":white_check_mark:", "failed": ":x:", "timeout": ":clock1:"}.get(
        status, ":question:"
    )

    text = (
        f"**Execution Verification** {status_emoji}\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| **ID** | `{result_id}` |\n"
        f"| **Language** | {language} |\n"
        f"| **Status** | {status} |\n"
        f"| **Attempts** | {attempts} |\n"
    )
    return await send_mattermost_notification(webhook_url, text)
