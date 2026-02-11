from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()
STATE: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SERVICE = 'template-library'
ENDPOINT = 'list_templates'

@router.get("/api/v1/templates")
async def list_templates(request) -> dict[str, Any]:
    path_key = None
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'template-library'
ENDPOINT = 'get_template'

@router.get("/api/v1/templates/{template_id}")
async def get_template(request, template_id: str) -> dict[str, Any]:
    path_key = template_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'template-library'
ENDPOINT = 'template_files'

@router.get("/api/v1/templates/{template_id}/files")
async def template_files(request, template_id: str) -> dict[str, Any]:
    path_key = template_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'template-library'
ENDPOINT = 'template_file_preview'

@router.get("/api/v1/templates/{template_id}/files/{path:path}")
async def template_file_preview(request, template_id: str) -> dict[str, Any]:
    path_key = template_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'template-library'
ENDPOINT = 'instantiate_template'

@router.post("/api/v1/templates/{template_id}/instantiate")
async def instantiate_template(request, template_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = template_id
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'template-library'
ENDPOINT = 'recommend_template'

@router.post("/api/v1/templates/recommend")
async def recommend_template(request, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = None
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}
