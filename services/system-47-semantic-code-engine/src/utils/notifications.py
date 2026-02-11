"""Mattermost notifications."""

from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger(__name__)


async def notify_mattermost(webhook_url: str, message: str) -> None:
    if not webhook_url:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json={"text": message})
            resp.raise_for_status()
    except Exception as exc:  # pragma: no cover
        logger.warning("mattermost_notify_failed", error=str(exc))
