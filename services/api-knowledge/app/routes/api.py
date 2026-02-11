from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()
STATE: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SERVICE = 'api-knowledge'
ENDPOINT = 'ingest_api'

@router.post("/api/v1/apis/ingest")
async def ingest_api(request, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = None
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'api-knowledge'
ENDPOINT = 'list_apis'

@router.get("/api/v1/apis")
async def list_apis(request) -> dict[str, Any]:
    path_key = None
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'api-knowledge'
ENDPOINT = 'get_api'

@router.get("/api/v1/apis/{name}")
async def get_api(request, name: str) -> dict[str, Any]:
    path_key = name
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'api-knowledge'
ENDPOINT = 'search_api'

@router.get("/api/v1/apis/{name}/search")
async def search_api(request, name: str) -> dict[str, Any]:
    path_key = name
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'api-knowledge'
ENDPOINT = 'list_endpoints'

@router.get("/api/v1/apis/{name}/endpoints")
async def list_endpoints(request, name: str) -> dict[str, Any]:
    path_key = name
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'api-knowledge'
ENDPOINT = 'endpoint_detail'

@router.get("/api/v1/apis/{name}/endpoints/{method}/{path:path}")
async def endpoint_detail(request, name: str) -> dict[str, Any]:
    path_key = name
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'api-knowledge'
ENDPOINT = 'pattern_for_use_case'

@router.get("/api/v1/patterns/{api}/{use_case}")
async def pattern_for_use_case(request, api: str) -> dict[str, Any]:
    path_key = api
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'api-knowledge'
ENDPOINT = 'pattern_for_use_case_lang'

@router.get("/api/v1/patterns/{api}/{use_case}/{language}")
async def pattern_for_use_case_lang(request, api: str) -> dict[str, Any]:
    path_key = api
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'api-knowledge'
ENDPOINT = 'check_updates'

@router.post("/api/v1/apis/{name}/check-updates")
async def check_updates(request, name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = name
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}
