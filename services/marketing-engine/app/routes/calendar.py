from datetime import date, timedelta
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import PlainTextResponse
from app.services.state import CALENDAR, uid

router = APIRouter()

@router.get('/api/v1/calendar')
async def get_calendar(start_date: str | None = Query(default=None), end_date: str | None = Query(default=None), channel: str | None = Query(default=None)):
    rows = list(CALENDAR.values())
    if start_date:
        rows = [r for r in rows if r['scheduled_date'] >= start_date]
    if end_date:
        rows = [r for r in rows if r['scheduled_date'] <= end_date]
    if channel:
        rows = [r for r in rows if r['channel'] == channel]
    return rows

@router.post('/api/v1/calendar', status_code=201)
async def create_entry(payload: dict):
    cid = uid()
    CALENDAR[cid] = {'id': cid, 'title': payload.get('title','Untitled'), 'content_type': payload.get('content_type','blog_post'), 'channel': payload.get('channel','content_marketing'), 'scheduled_date': payload.get('scheduled_date', date.today().isoformat()), 'status': payload.get('status','planned'), 'content_brief': payload.get('content_brief',''), 'keywords': payload.get('keywords',[])}
    return CALENDAR[cid]

@router.put('/api/v1/calendar/{entry_id}')
async def update_entry(entry_id: str, payload: dict):
    if entry_id not in CALENDAR:
        raise HTTPException(status_code=404, detail='entry not found')
    CALENDAR[entry_id].update(payload)
    return CALENDAR[entry_id]

@router.delete('/api/v1/calendar/{entry_id}')
async def delete_entry(entry_id: str):
    if entry_id not in CALENDAR:
        raise HTTPException(status_code=404, detail='entry not found')
    CALENDAR.pop(entry_id, None)
    return {'deleted': True}

@router.post('/api/v1/calendar/generate')
async def generate(payload: dict):
    days = int(payload.get('days', 30))
    goals = payload.get('goals', [])
    channels = payload.get('channels', ['email'])
    entries = []
    for idx in range(min(days, 90)):
        if idx % max(1, days // 10) == 0:
            cid = uid()
            row = {'id': cid, 'date': (date.today()+timedelta(days=idx)).isoformat(), 'title': f"Content {idx+1}", 'type': 'content_marketing', 'channel': channels[idx % len(channels)], 'brief': f"Goals: {', '.join(goals)}", 'keywords': ['omni','growth']}
            entries.append(row)
            CALENDAR[cid] = {'id': cid, 'title': row['title'], 'content_type': row['type'], 'channel': row['channel'], 'scheduled_date': row['date'], 'status': 'planned', 'content_brief': row['brief'], 'keywords': row['keywords']}
    return {'entries': entries}

@router.get('/api/v1/calendar/export')
async def export_calendar():
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Omni Quantum Elite//Marketing Calendar//EN']
    for row in CALENDAR.values():
        lines.extend(['BEGIN:VEVENT', f"UID:{row['id']}", f"DTSTART;VALUE=DATE:{row['scheduled_date'].replace('-', '')}", f"SUMMARY:{row['title']}", f"DESCRIPTION:{row.get('content_brief','')}", 'END:VEVENT'])
    lines.append('END:VCALENDAR')
    return PlainTextResponse('\n'.join(lines), media_type='text/calendar')
