from fastapi import APIRouter, HTTPException

router = APIRouter()
COMPETITORS = {}
COMP_POSTS = {}

@router.post('/api/v1/competitors', status_code=201)
async def add_competitor(payload: dict):
    cid = str(len(COMPETITORS)+1)
    COMPETITORS[cid] = {'id': cid, 'platform': payload.get('platform','twitter'), 'account_handle': payload.get('handle','unknown'), 'follower_count': 1000, 'avg_engagement_rate': 0.04, 'content_strategy_summary': 'mix of educational and proof content'}
    COMP_POSTS[cid] = []
    return COMPETITORS[cid]

@router.get('/api/v1/competitors')
async def list_competitors():
    return list(COMPETITORS.values())

@router.get('/api/v1/competitors/leaderboard')
async def leaderboard():
    rows = list(COMPETITORS.values())
    rows.sort(key=lambda x: (x.get('follower_count', 0), x.get('avg_engagement_rate', 0.0)), reverse=True)
    return rows

@router.get('/api/v1/competitors/content-gaps')
async def gaps(our_topics: str = ''):
    ours = {x.strip().lower() for x in our_topics.split(',') if x.strip()}
    all_topics = {'benchmarking', 'automation', 'founder-story', 'pricing-breakdown'}
    miss = sorted(all_topics.difference(ours))
    return {'gaps': miss, 'recommended_focus': miss[:3]}

@router.get('/api/v1/competitors/strategies')
async def strategies():
    return [{'competitor_id': c['id'], 'handle': c['account_handle'], 'strategy': c['content_strategy_summary']} for c in COMPETITORS.values()]

@router.post('/api/v1/competitors/steal-strategy')
async def steal_strategy():
    return {'playbook': ['publish one educational thread daily', 'post proof-driven case study twice weekly', 'use trend hooks with clear CTA']}

@router.get('/api/v1/competitors/{competitor_id}')
async def get_competitor(competitor_id: str):
    if competitor_id not in COMPETITORS:
        raise HTTPException(status_code=404, detail='competitor not found')
    out = dict(COMPETITORS[competitor_id])
    out['posts'] = COMP_POSTS.get(competitor_id, [])
    return out

@router.post('/api/v1/competitors/{competitor_id}/analyze')
async def analyze(competitor_id: str):
    if competitor_id not in COMPETITORS:
        raise HTTPException(status_code=404, detail='competitor not found')
    post = {'id': str(len(COMP_POSTS[competitor_id])+1), 'text_content': 'high-performing post', 'content_format': 'text', 'likes': 500, 'comments': 45, 'shares': 30, 'engagement_rate': 0.062, 'is_viral': True}
    COMP_POSTS.setdefault(competitor_id, []).append(post)
    return {'competitor': COMPETITORS[competitor_id], 'latest_post': post}

@router.get('/api/v1/competitors/{competitor_id}/posts')
async def posts(competitor_id: str):
    if competitor_id not in COMPETITORS:
        raise HTTPException(status_code=404, detail='competitor not found')
    return COMP_POSTS.get(competitor_id, [])
