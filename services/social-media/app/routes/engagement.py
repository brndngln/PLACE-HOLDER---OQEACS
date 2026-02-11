from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

router = APIRouter()
QUEUE = {}
AUTO = {'enabled': False, 'rules': []}

def _seed():
    if not QUEUE:
        QUEUE['1'] = {'id':'1','platform':'twitter','interaction_type':'comment','content':'How do I get started?','sentiment':'question','priority':2,'status':'pending','suggested_response':'Thanks for asking. Start with docs.','created_at':datetime.now(timezone.utc).isoformat()}

@router.get('/api/v1/engagement/queue')
async def queue():
    _seed()
    return list(QUEUE.values())

@router.get('/api/v1/engagement/queue/{item_id}')
async def item(item_id: str):
    if item_id not in QUEUE:
        raise HTTPException(status_code=404, detail='item not found')
    return QUEUE[item_id]

@router.post('/api/v1/engagement/queue/{item_id}/respond')
async def respond(item_id: str, payload: dict):
    if item_id not in QUEUE:
        raise HTTPException(status_code=404, detail='item not found')
    QUEUE[item_id]['actual_response'] = payload.get('response','Thanks')
    QUEUE[item_id]['status'] = 'responded'
    QUEUE[item_id]['responded_at'] = datetime.now(timezone.utc).isoformat()
    return QUEUE[item_id]

@router.post('/api/v1/engagement/queue/{item_id}/ignore')
async def ignore(item_id: str):
    if item_id not in QUEUE:
        raise HTTPException(status_code=404, detail='item not found')
    QUEUE[item_id]['status'] = 'ignored'
    return QUEUE[item_id]

@router.post('/api/v1/engagement/queue/{item_id}/flag')
async def flag(item_id: str):
    if item_id not in QUEUE:
        raise HTTPException(status_code=404, detail='item not found')
    QUEUE[item_id]['status'] = 'flagged'
    return QUEUE[item_id]

@router.get('/api/v1/engagement/sentiment')
async def sentiment():
    _seed()
    out = {'positive':0,'neutral':0,'negative':0,'question':0}
    for it in QUEUE.values():
        out[it.get('sentiment','neutral')] = out.get(it.get('sentiment','neutral'),0)+1
    return out

@router.post('/api/v1/engagement/auto-respond/config')
async def auto(payload: dict):
    AUTO.update(payload)
    return AUTO
