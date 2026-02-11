from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException

router = APIRouter()
TRENDS = {}

@router.get('/api/v1/trends')
async def list_trends(platform: str | None = None, category: str | None = None, min_relevance: float | None = None):
    rows = list(TRENDS.values())
    if platform:
        rows = [r for r in rows if r.get('platform') == platform]
    if category:
        rows = [r for r in rows if r.get('category') == category]
    if min_relevance is not None:
        rows = [r for r in rows if float(r.get('relevance_score',0)) >= min_relevance]
    return rows

@router.get('/api/v1/trends/{trend_id}')
async def get_trend(trend_id: str):
    if trend_id not in TRENDS:
        raise HTTPException(status_code=404, detail='trend not found')
    return TRENDS[trend_id]

@router.post('/api/v1/trends/scan')
async def scan():
    samples = [('twitter','ai agents','tech',0.92),('linkedin','enterprise automation','business',0.86),('instagram','build in public','culture',0.81)]
    out = []
    for idx, sample in enumerate(samples):
        tid = str(len(TRENDS)+1+idx)
        p, topic, cat, rel = sample
        row = {'id': tid, 'platform': p, 'topic': topic, 'hashtag': '#' + topic.replace(' ','').lower(), 'category': cat, 'relevance_score': rel, 'recommended_action': 'post_now' if rel > 0.85 else 'monitor', 'source': 'scanner', 'detected_at': datetime.now(timezone.utc).isoformat(), 'expires_at': (datetime.now(timezone.utc)+timedelta(hours=12)).isoformat()}
        TRENDS[tid] = row
        out.append(row)
    return {'trends': out}

@router.post('/api/v1/trends/{trend_id}/create-post')
async def create_post_from_trend(trend_id: str, payload: dict):
    if trend_id not in TRENDS:
        raise HTTPException(status_code=404, detail='trend not found')
    platforms = payload.get('platforms', [TRENDS[trend_id]['platform']])
    return {'posts': {p: {'text': f"{TRENDS[trend_id]['topic']} for {p}", 'hashtags': [TRENDS[trend_id]['hashtag']]} for p in platforms}}

@router.post('/api/v1/trends/subscribe')
async def subscribe(payload: dict):
    return {'subscribed': True, 'feed': payload}

@router.get('/api/v1/trends/history')
async def history():
    return list(TRENDS.values())
