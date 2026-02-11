from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()
STATE: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SERVICE = 'ui-intelligence'
ENDPOINT = 'search_knowledge'

@router.get("/api/v1/knowledge/search")
async def search_knowledge(request) -> dict[str, Any]:
    path_key = None
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'ui-intelligence'
ENDPOINT = 'framework_rules'

@router.get("/api/v1/rules/{framework}")
async def framework_rules(request, framework: str) -> dict[str, Any]:
    path_key = framework
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'ui-intelligence'
ENDPOINT = 'validate_ui'

@router.post("/api/v1/validate")
async def validate_ui(request, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = None
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'ui-intelligence'
ENDPOINT = 'recommend_components'

@router.post("/api/v1/components/recommend")
async def recommend_components(request, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = None
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}
