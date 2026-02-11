from fastapi import APIRouter, HTTPException
from app.models.requests import CreateAudienceRequest
from app.services.state import AUDIENCES, LEADS, uid, now

router = APIRouter()

@router.post('/api/v1/audiences', status_code=201)
async def create(payload: CreateAudienceRequest):
    aid = uid()
    AUDIENCES[aid] = {'id': aid, 'name': payload.name, 'description': payload.description, 'segment_rules': payload.segment_rules, 'member_count': 0, 'created_at': now(), 'updated_at': now()}
    return AUDIENCES[aid]

@router.get('/api/v1/audiences')
async def list_audiences():
    return list(AUDIENCES.values())

@router.get('/api/v1/audiences/{audience_id}')
async def get_audience(audience_id: str):
    if audience_id not in AUDIENCES:
        raise HTTPException(status_code=404, detail='audience not found')
    return AUDIENCES[audience_id]

@router.put('/api/v1/audiences/{audience_id}')
async def update_audience(audience_id: str, payload: dict):
    if audience_id not in AUDIENCES:
        raise HTTPException(status_code=404, detail='audience not found')
    AUDIENCES[audience_id].update(payload)
    AUDIENCES[audience_id]['updated_at'] = now()
    return AUDIENCES[audience_id]

@router.get('/api/v1/audiences/{audience_id}/members')
async def members(audience_id: str):
    if audience_id not in AUDIENCES:
        raise HTTPException(status_code=404, detail='audience not found')
    return {'audience_id': audience_id, 'members': list(LEADS.values())}

@router.post('/api/v1/audiences/{audience_id}/refresh')
async def refresh(audience_id: str):
    if audience_id not in AUDIENCES:
        raise HTTPException(status_code=404, detail='audience not found')
    AUDIENCES[audience_id]['member_count'] = len(LEADS)
    return {'audience_id': audience_id, 'member_count': len(LEADS)}
