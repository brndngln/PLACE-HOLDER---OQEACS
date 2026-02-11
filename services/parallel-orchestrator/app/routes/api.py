from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()
STATE: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SERVICE = 'parallel-orchestrator'
ENDPOINT = 'decompose_project'

@router.post("/api/v1/projects/decompose")
async def decompose_project(request, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = None
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'parallel-orchestrator'
ENDPOINT = 'execute_project'

@router.post("/api/v1/projects/{project_id}/execute")
async def execute_project(request, project_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = project_id
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'parallel-orchestrator'
ENDPOINT = 'get_project'

@router.get("/api/v1/projects/{project_id}")
async def get_project(request, project_id: str) -> dict[str, Any]:
    path_key = project_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'parallel-orchestrator'
ENDPOINT = 'list_subtasks'

@router.get("/api/v1/projects/{project_id}/subtasks")
async def list_subtasks(request, project_id: str) -> dict[str, Any]:
    path_key = project_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'parallel-orchestrator'
ENDPOINT = 'get_subtask'

@router.get("/api/v1/projects/{project_id}/subtasks/{subtask_id}")
async def get_subtask(request, project_id: str) -> dict[str, Any]:
    path_key = project_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}


SERVICE = 'parallel-orchestrator'
ENDPOINT = 'abort_project'

@router.post("/api/v1/projects/{project_id}/abort")
async def abort_project(request, project_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    path_key = project_id
    payload = payload or {}
    key = path_key or payload.get('id') or f'item-{uuid.uuid4().hex[:10]}'
    record = {'id': key, 'payload': payload, 'updated_at': _now(), 'endpoint': ENDPOINT}
    STATE[key] = record
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'item': record, 'total': len(STATE)}


SERVICE = 'parallel-orchestrator'
ENDPOINT = 'list_merges'

@router.get("/api/v1/projects/{project_id}/merges")
async def list_merges(request, project_id: str) -> dict[str, Any]:
    path_key = project_id
    if path_key and path_key not in STATE:
        raise HTTPException(status_code=404, detail='not found')
    return {'ok': True, 'service': SERVICE, 'endpoint': ENDPOINT, 'path_key': path_key, 'items': list(STATE.values()) if path_key is None else STATE[path_key]}
