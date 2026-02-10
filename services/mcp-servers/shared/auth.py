from __future__ import annotations

import os
import time
from dataclasses import dataclass

from fastapi import Header, HTTPException


@dataclass
class ClientInfo:
    client_name: str
    permissions: list[str]


_RATE: dict[str, list[float]] = {}


def validate_api_key(key: str) -> ClientInfo:
    # Vault-backed lookup can be wired by setting MCP_KEYS_JSON='{"client":"key"}'
    mapping = os.getenv("MCP_KEYS_JSON", "{}")
    import json

    keys = json.loads(mapping)
    for client, value in keys.items():
        if value == key:
            return ClientInfo(client_name=client, permissions=["*"])
    fallback = os.getenv("MCP_DEFAULT_API_KEY", "")
    if fallback and key == fallback:
        return ClientInfo(client_name="default-client", permissions=["*"])
    raise HTTPException(status_code=401, detail="Invalid MCP API key")


def enforce_rate_limit(client_name: str, limit: int = 100, window_seconds: int = 60) -> None:
    now = time.time()
    arr = _RATE.setdefault(client_name, [])
    arr[:] = [t for t in arr if now - t < window_seconds]
    if len(arr) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded; retry after 60 seconds")
    arr.append(now)


def get_client_info(x_mcp_api_key: str | None = Header(default=None), api_key: str | None = None) -> ClientInfo:
    key = x_mcp_api_key or api_key
    if not key:
        raise HTTPException(status_code=401, detail="Missing MCP API key")
    info = validate_api_key(key)
    enforce_rate_limit(info.client_name)
    return info
