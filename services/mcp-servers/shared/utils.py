from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


def format_for_mcp(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def truncate_response(text: str, max_tokens: int = 4000) -> str:
    max_chars = max_tokens * 4
    return text if len(text) <= max_chars else text[: max_chars - 3] + "..."


def call_service(url: str, method: str = "GET", json: dict[str, Any] | None = None, timeout: float = 30) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.request(method, url, json=json)
            resp.raise_for_status()
            if not resp.text:
                return {}
            return resp.json()
    except Exception as exc:
        logger.error("service_call_failed", url=url, method=method, error=str(exc))
        raise
