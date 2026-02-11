from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()
STATE: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SERVICE = 'runtime-manager'
ENDPOINT = 'list_runtimes'

@router.get("/api/v1/runtimes")
async def list_runtimes(request) -> dict[str, Any]:
    path_key = None
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'runtime-manager'
ENDPOINT = 'get_runtime'

@router.get("/api/v1/runtimes/{language}/{version}")
async def get_runtime(request, language: str) -> dict[str, Any]:
    path_key = language
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'runtime-manager'
ENDPOINT = 'trigger_build'

@router.post("/api/v1/runtimes/build")
async def trigger_build(request, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = None
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'runtime-manager'
ENDPOINT = 'build_status'

@router.get("/api/v1/runtimes/build/{build_id}")
async def build_status(request, build_id: str) -> dict[str, Any]:
    path_key = build_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'runtime-manager'
ENDPOINT = 'delete_runtime'

@router.delete("/api/v1/runtimes/{language}/{version}")
async def delete_runtime(request, language: str) -> dict[str, Any]:
    path_key = language
    if path_key and path_key in STATE:
        STATE.pop(path_key, None)
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'deleted': path_key}


SERVICE = 'runtime-manager'
ENDPOINT = 'runtime_status'

@router.get("/api/v1/runtimes/status")
async def runtime_status(request) -> dict[str, Any]:
    path_key = None
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}



RUNTIMES = {
    "python:3.12": {"language": "python", "version": "3.12", "image_name": "omni-runtime-python:3.12", "tools": ["pytest", "ruff", "mypy", "black"]},
    "python:3.11": {"language": "python", "version": "3.11", "image_name": "omni-runtime-python:3.11", "tools": ["pytest", "ruff", "mypy", "black"]},
    "node:22": {"language": "node", "version": "22", "image_name": "omni-runtime-node:22", "tools": ["typescript", "eslint", "vitest"]},
    "go:1.22": {"language": "go", "version": "1.22", "image_name": "omni-runtime-go:1.22", "tools": ["golangci-lint", "govulncheck"]},
}
