from fastapi import APIRouter, HTTPException
from app.models.requests import CreateCompetitorRequest
from app.services.state import COMPETITORS, COMPETITOR_SNAPSHOTS, uid, now

router = APIRouter()

@router.post('/api/v1/competitors', status_code=201)
async def create(payload: CreateCompetitorRequest):
    cid = uid()
    COMPETITORS[cid] = {'id': cid, 'name': payload.name, 'website': payload.website, 'description': '', 'pricing_model': 'unknown', 'target_market': 'unknown', 'created_at': now()}
    COMPETITOR_SNAPSHOTS[cid] = []
    return COMPETITORS[cid]

@router.get('/api/v1/competitors')
async def list_competitors():
    return list(COMPETITORS.values())

@router.get('/api/v1/competitors/{competitor_id}')
async def get_competitor(competitor_id: str):
    if competitor_id not in COMPETITORS:
        raise HTTPException(status_code=404, detail='competitor not found')
    out = dict(COMPETITORS[competitor_id])
    out['latest_snapshots'] = COMPETITOR_SNAPSHOTS.get(competitor_id, [])[-3:]
    return out

@router.post('/api/v1/competitors/{competitor_id}/analyze')
async def analyze(competitor_id: str):
    if competitor_id not in COMPETITORS:
        raise HTTPException(status_code=404, detail='competitor not found')
    snap = {'id': uid(), 'snapshot_type': 'strategy', 'content': 'competitor focuses on social proof and speed', 'url': COMPETITORS[competitor_id].get('website'), 'changes_detected': 'new pricing section', 'features': ['case studies','free trial'], 'pricing': 'tiered', 'analyzed_at': now()}
    COMPETITOR_SNAPSHOTS.setdefault(competitor_id, []).append(snap)
    return snap

@router.get('/api/v1/competitors/{competitor_id}/history')
async def history(competitor_id: str):
    if competitor_id not in COMPETITORS:
        raise HTTPException(status_code=404, detail='competitor not found')
    return COMPETITOR_SNAPSHOTS.get(competitor_id, [])

@router.get('/api/v1/competitors/comparison')
async def comparison():
    return {'rows': [{'id': c['id'], 'name': c['name'], 'pricing_model': c.get('pricing_model','unknown')} for c in COMPETITORS.values()]}

@router.post('/api/v1/competitors/gaps')
async def gaps(payload: dict):
    return {'gaps': [{'area': 'onboarding', 'description': 'Competitors offer guided setup', 'opportunity_size': 'high', 'recommended_action': 'launch concierge onboarding'}], 'our_features': payload.get('our_features',[]), 'our_pricing': payload.get('our_pricing','unknown')}
