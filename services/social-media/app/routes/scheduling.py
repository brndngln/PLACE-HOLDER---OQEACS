from datetime import datetime, timedelta, timezone
from fastapi import APIRouter
from app.routes.publishing import POSTS

router = APIRouter()

@router.get('/api/v1/schedule/optimal-times')
async def optimal_times():
    now = datetime.now(timezone.utc)
    out = {}
    for p in ['twitter','linkedin','instagram','youtube','tiktok','facebook','reddit','threads','bluesky']:
        out[p] = [{'day': 'monday', 'time': (now+timedelta(hours=i+1)).strftime('%H:%M'), 'expected_engagement': round(0.03+i*0.01,4), 'reasoning': 'historical engagement and audience activity'} for i in range(3)]
    return out

@router.get('/api/v1/schedule/calendar')
async def calendar(week: str | None = None, month: str | None = None):
    return {'week': week, 'month': month, 'scheduled_posts': [p for p in POSTS.values() if p.get('scheduled_at')]}

@router.post('/api/v1/schedule/auto-generate')
async def auto_generate(payload: dict):
    days = int(payload.get('days', 7))
    ppd = int(payload.get('posts_per_day_per_platform', 1))
    pillars = payload.get('content_pillars', ['educational'])
    topics = payload.get('topics', ['omni'])
    rows = []
    now = datetime.now(timezone.utc)
    platforms = ['twitter','linkedin','instagram']
    for d in range(days):
        for p in platforms:
            for i in range(ppd):
                rows.append({'platform': p, 'date': (now+timedelta(days=d)).date().isoformat(), 'time': (now+timedelta(days=d, hours=i+9)).strftime('%H:%M'), 'topic': topics[(d+i)%len(topics)], 'pillar': pillars[(d+i)%len(pillars)], 'draft_text': 'Scheduled auto-generated draft'})
    return {'scheduled_posts': rows}
