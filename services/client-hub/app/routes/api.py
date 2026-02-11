from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()
STATE: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SERVICE = 'client-hub'
ENDPOINT = 'project_status'

@router.get("/api/v1/projects/{project_id}/status")
async def project_status(request, project_id: str) -> dict[str, Any]:
    path_key = project_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'client-hub'
ENDPOINT = 'create_preview'

@router.post("/api/v1/projects/{project_id}/preview")
async def create_preview(request, project_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = project_id
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'client-hub'
ENDPOINT = 'get_preview'

@router.get("/api/v1/projects/{project_id}/preview")
async def get_preview(request, project_id: str) -> dict[str, Any]:
    path_key = project_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'client-hub'
ENDPOINT = 'submit_approval'

@router.post("/api/v1/projects/{project_id}/approvals")
async def submit_approval(request, project_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = project_id
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'client-hub'
ENDPOINT = 'approve'

@router.post("/api/v1/projects/{project_id}/approvals/{approval_id}/approve")
async def approve(request, project_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = project_id
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'client-hub'
ENDPOINT = 'reject'

@router.post("/api/v1/projects/{project_id}/approvals/{approval_id}/reject")
async def reject(request, project_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = project_id
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'client-hub'
ENDPOINT = 'deliver'

@router.post("/api/v1/projects/{project_id}/deliver")
async def deliver(request, project_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = project_id
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'client-hub'
ENDPOINT = 'deliveries'

@router.get("/api/v1/projects/{project_id}/deliveries")
async def deliveries(request, project_id: str) -> dict[str, Any]:
    path_key = project_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'client-hub'
ENDPOINT = 'activity'

@router.get("/api/v1/projects/{project_id}/activity")
async def activity(request, project_id: str) -> dict[str, Any]:
    path_key = project_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}



@router.websocket("/ws/projects/{project_id}")
async def ws_project_progress(websocket, project_id: str):
    await websocket.accept()
    await websocket.send_json({"project_id": project_id, "status": "connected", "timestamp": _now()})
    await websocket.close()
