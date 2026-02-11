from __future__ import annotations

import httpx


async def notify_mattermost(webhook_url: str, text: str) -> bool:
    if not webhook_url:
        return False
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(webhook_url, json={"text": text})
        return response.is_success
