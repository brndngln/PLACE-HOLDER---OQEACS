from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from app.models.requests import CreatePostRequest

router = APIRouter()
POSTS = {}

@router.post('/api/v1/posts', status_code=201)
async def create_post(payload: CreatePostRequest):
    pid = str(len(POSTS)+1)
    POSTS[pid] = {'id': pid, 'account_id': payload.account_id, 'platform': payload.platform, 'status': 'draft', 'content_format': payload.format, 'text_content': payload.text, 'media_urls': payload.media_urls, 'scheduled_at': payload.scheduled_at, 'published_at': None, 'platform_post_id': None, 'engagement_rate': 0.0, 'likes': 0, 'comments': 0, 'shares': 0, 'saves': 0, 'clicks': 0, 'created_at': datetime.now(timezone.utc).isoformat(), 'updated_at': datetime.now(timezone.utc).isoformat()}
    if payload.scheduled_at:
        POSTS[pid]['status'] = 'scheduled'
    return POSTS[pid]

@router.get('/api/v1/posts')
async def list_posts(status: str | None = Query(default=None), platform: str | None = Query(default=None), date_range: str | None = Query(default=None), pillar: str | None = Query(default=None)):
    _ = date_range
    _ = pillar
    rows = list(POSTS.values())
    if status:
        rows = [r for r in rows if r['status']==status]
    if platform:
        rows = [r for r in rows if r['platform']==platform]
    return rows

@router.get('/api/v1/posts/{post_id}')
async def get_post(post_id: str):
    if post_id not in POSTS:
        raise HTTPException(status_code=404, detail='post not found')
    return POSTS[post_id]

@router.put('/api/v1/posts/{post_id}')
async def update_post(post_id: str, payload: dict):
    if post_id not in POSTS:
        raise HTTPException(status_code=404, detail='post not found')
    if POSTS[post_id]['status']=='published':
        raise HTTPException(status_code=409, detail='published posts are immutable')
    POSTS[post_id].update(payload)
    POSTS[post_id]['updated_at'] = datetime.now(timezone.utc).isoformat()
    return POSTS[post_id]

@router.delete('/api/v1/posts/{post_id}')
async def delete_post(post_id: str):
    if post_id not in POSTS:
        raise HTTPException(status_code=404, detail='post not found')
    POSTS.pop(post_id, None)
    return {'deleted': True}

@router.post('/api/v1/posts/{post_id}/publish')
async def publish(post_id: str):
    if post_id not in POSTS:
        raise HTTPException(status_code=404, detail='post not found')
    POSTS[post_id]['status'] = 'published'
    POSTS[post_id]['published_at'] = datetime.now(timezone.utc).isoformat()
    POSTS[post_id]['platform_post_id'] = f"platform-{post_id}"
    POSTS[post_id]['engagement_rate'] = 0.06
    return POSTS[post_id]

@router.post('/api/v1/posts/{post_id}/schedule')
async def schedule(post_id: str, payload: dict):
    if post_id not in POSTS:
        raise HTTPException(status_code=404, detail='post not found')
    POSTS[post_id]['scheduled_at'] = payload.get('scheduled_at')
    POSTS[post_id]['status'] = 'scheduled'
    return POSTS[post_id]

@router.post('/api/v1/posts/bulk-schedule')
async def bulk_schedule(payload: dict):
    rows = []
    for row in payload.get('posts', []):
        created = await create_post(CreatePostRequest(text=row['text'], platform=row['platform'], account_id=row.get('account_id','bulk'), media_urls=row.get('media_urls',[]), format=row.get('format','text'), scheduled_at=row.get('scheduled_at')))
        rows.append(created)
    return {'scheduled': len(rows), 'posts': rows}

@router.get('/api/v1/posts/queue')
async def queue():
    return [r for r in POSTS.values() if r['status']=='scheduled']

@router.post('/api/v1/posts/cross-post')
async def cross_post(payload: dict):
    rows = []
    for p in payload.get('platforms', []):
        txt = payload.get('text','')
        if payload.get('adapt_per_platform', True):
            txt = f"[{p}] {txt}"
        created = await create_post(CreatePostRequest(text=txt, platform=p, account_id=payload.get('account_id','multi'), media_urls=payload.get('media_urls',[]), format=payload.get('format','text'), scheduled_at=None))
        rows.append(created)
    return {'posts': rows}
