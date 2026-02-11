from fastapi import APIRouter, HTTPException
from app.models.requests import GenerateContentRequest, RepurposeRequest, HashtagResearchRequest
from app.routes.accounts import ACCOUNTS
from app.routes.publishing import POSTS

router = APIRouter()

LIMITS = {'twitter': 280, 'linkedin': 3000, 'instagram': 2200, 'youtube': 5000, 'tiktok': 4000, 'facebook': 63206, 'reddit': 40000, 'threads': 500, 'bluesky': 300}

@router.post('/api/v1/content/generate')
async def generate(payload: GenerateContentRequest):
    out = {}
    for p in payload.platforms:
        text = f"{payload.topic} | {payload.content_pillar} | {payload.tone}"[:LIMITS.get(p,500)]
        out[p] = {'text': text, 'hashtags': [f"#{payload.topic.replace(' ','')}", '#omni'], 'media_brief': f"Visual for {payload.topic}", 'format_type': 'thread' if p=='twitter' else 'text', 'character_count': len(text), 'estimated_engagement': 0.05, 'optimal_post_time': '09:00'}
    return {'posts': out}

@router.post('/api/v1/content/repurpose')
async def repurpose(payload: RepurposeRequest):
    if payload.source_post_id not in POSTS:
        raise HTTPException(status_code=404, detail='source post not found')
    src = POSTS[payload.source_post_id]['text_content']
    return {'variants': {p: {'text': (f"Repurposed for {p}: {src}")[:LIMITS.get(p,500)], 'platform': p} for p in payload.target_platforms}}

@router.post('/api/v1/content/improve')
async def improve(payload: dict):
    text = payload.get('content', '')
    goals = payload.get('goals', [])
    if 'more_engaging' in goals:
        text = 'Hook: ' + text
    if 'shorter' in goals:
        text = text[:max(40, int(len(text)*0.75))]
    return {'improved_text': text, 'changes_made': goals, 'improvement_score': 0.88}

@router.post('/api/v1/content/hashtag-research')
async def hashtags(payload: HashtagResearchRequest):
    return {'hashtags': [{'tag': f"#{payload.topic.replace(' ','')}{i+1}", 'volume': 100000-(i*1000), 'competition': round(0.2+i*0.02,2), 'relevance_score': round(0.95-i*0.01,2)} for i in range(payload.count)]}
