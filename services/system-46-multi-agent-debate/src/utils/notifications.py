"""System 46 — Mattermost notification helper."""

from __future__ import annotations

import httpx
import structlog

from src.config import Settings

logger = structlog.get_logger()

_SEVERITY_EMOJI: dict[str, str] = {
    "info": ":information_source:",
    "success": ":white_check_mark:",
    "warning": ":warning:",
    "error": ":x:",
    "critical": ":rotating_light:",
    "debate": ":speaking_head:",
    "consensus": ":handshake:",
    "deadlock": ":lock:",
}


async def notify_mattermost(
    message: str,
    severity: str = "info",
    *,
    settings: Settings | None = None,
) -> None:
    """Post a notification to the configured Mattermost webhook."""
    _settings = settings or Settings()
    emoji = _SEVERITY_EMOJI.get(severity, ":speech_balloon:")
    payload = {"text": f"{emoji} **[Debate Engine]** {message}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_settings.MATTERMOST_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("mattermost_notify_failed", error=str(exc))
