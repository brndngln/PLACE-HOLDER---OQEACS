from fastapi import APIRouter, HTTPException
from app.models.requests import CreateSequenceRequest
from app.services.state import SEQUENCES, uid, now

router = APIRouter()

@router.post('/api/v1/sequences', status_code=201)
async def create_sequence(payload: CreateSequenceRequest):
    sid = uid()
    SEQUENCES[sid] = {'id': sid, 'campaign_id': payload.campaign_id, 'name': payload.name, 'trigger_event': payload.trigger_event, 'status': 'draft', 'steps': [], 'created_at': now()}
    return SEQUENCES[sid]

@router.get('/api/v1/sequences')
async def list_sequences():
    return list(SEQUENCES.values())

@router.get('/api/v1/sequences/{sequence_id}')
async def get_sequence(sequence_id: str):
    if sequence_id not in SEQUENCES:
        raise HTTPException(status_code=404, detail='sequence not found')
    return SEQUENCES[sequence_id]

@router.put('/api/v1/sequences/{sequence_id}')
async def update_sequence(sequence_id: str, payload: dict):
    if sequence_id not in SEQUENCES:
        raise HTTPException(status_code=404, detail='sequence not found')
    SEQUENCES[sequence_id].update(payload)
    return SEQUENCES[sequence_id]

@router.post('/api/v1/sequences/{sequence_id}/steps')
async def add_step(sequence_id: str, payload: dict):
    if sequence_id not in SEQUENCES:
        raise HTTPException(status_code=404, detail='sequence not found')
    step = {'step_number': int(payload.get('step_number', len(SEQUENCES[sequence_id]['steps'])+1)), 'delay_hours': int(payload.get('delay_hours', 24)), 'subject_line': payload.get('subject_line', 'Update'), 'body_html': payload.get('body_html', '<p>Body</p>'), 'sent_count': 0, 'open_count': 0, 'click_count': 0, 'unsubscribe_count': 0}
    SEQUENCES[sequence_id]['steps'].append(step)
    return step

@router.put('/api/v1/sequences/{sequence_id}/steps/{step_number}')
async def update_step(sequence_id: str, step_number: int, payload: dict):
    if sequence_id not in SEQUENCES:
        raise HTTPException(status_code=404, detail='sequence not found')
    step = next((s for s in SEQUENCES[sequence_id]['steps'] if s['step_number']==step_number), None)
    if not step:
        raise HTTPException(status_code=404, detail='step not found')
    step.update(payload)
    return step

@router.delete('/api/v1/sequences/{sequence_id}/steps/{step_number}')
async def delete_step(sequence_id: str, step_number: int):
    if sequence_id not in SEQUENCES:
        raise HTTPException(status_code=404, detail='sequence not found')
    before = len(SEQUENCES[sequence_id]['steps'])
    SEQUENCES[sequence_id]['steps'] = [s for s in SEQUENCES[sequence_id]['steps'] if s['step_number'] != step_number]
    if len(SEQUENCES[sequence_id]['steps']) == before:
        raise HTTPException(status_code=404, detail='step not found')
    return {'deleted': True}

@router.post('/api/v1/sequences/{sequence_id}/activate')
async def activate(sequence_id: str):
    if sequence_id not in SEQUENCES:
        raise HTTPException(status_code=404, detail='sequence not found')
    SEQUENCES[sequence_id]['status'] = 'active'
    return SEQUENCES[sequence_id]

@router.post('/api/v1/sequences/{sequence_id}/pause')
async def pause(sequence_id: str):
    if sequence_id not in SEQUENCES:
        raise HTTPException(status_code=404, detail='sequence not found')
    SEQUENCES[sequence_id]['status'] = 'paused'
    return SEQUENCES[sequence_id]

@router.get('/api/v1/sequences/{sequence_id}/metrics')
async def metrics(sequence_id: str):
    if sequence_id not in SEQUENCES:
        raise HTTPException(status_code=404, detail='sequence not found')
    return {'sequence_id': sequence_id, 'steps': SEQUENCES[sequence_id]['steps'], 'status': SEQUENCES[sequence_id]['status']}
