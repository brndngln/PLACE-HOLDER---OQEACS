from fastapi import APIRouter
from app.routes.accounts import ACCOUNTS

router = APIRouter()

@router.get('/api/v1/strategy/recommendations')
async def recommendations():
    return {'recommendations': [{'area':'content cadence','action':'Increase LinkedIn posting to 2/day','expected_impact':'high','difficulty':'medium','timeline':'2 weeks','reasoning':'LinkedIn currently has highest conversion quality'},{'area':'trend execution','action':'Publish trend response content within 60 minutes','expected_impact':'high','difficulty':'medium','timeline':'1 week','reasoning':'Trend freshness strongly correlates with reach gains'}]}

@router.post('/api/v1/strategy/audit')
async def audit():
    scores = [{'platform': a['platform'], 'health_score': 78, 'strengths': ['consistent cadence'], 'weaknesses': ['underutilized video'], 'opportunities': ['collab posts'], 'threats': ['rapid competitor growth']} for a in ACCOUNTS.values()]
    return {'account_scores': scores, 'overall_score': 80, 'priority_actions': ['increase video output', 'add platform-specific hooks']}

@router.get('/api/v1/strategy/content-mix')
async def content_mix():
    return {'pillars': [{'name':'educational','target_pct':35.0,'actual_pct':28.0,'avg_engagement':0.05,'recommendation':'increase'},{'name':'entertaining','target_pct':20.0,'actual_pct':24.0,'avg_engagement':0.047,'recommendation':'hold'}]}

@router.post('/api/v1/strategy/100m-plan')
async def plan_100m():
    total = sum(int(a.get('follower_count',0)) for a in ACCOUNTS.values())
    return {'current_followers': total, 'phases': [{'name':'Foundation','target':1000000,'timeline':'0-6 months','platforms_focus':['twitter','linkedin','instagram'],'content_strategy':'daily educational + proof content','growth_tactics':['collabs','cross-posting','trend riding'],'budget_estimate':5000,'key_metrics':['engagement_rate','weekly_follower_delta']},{'name':'Scale','target':10000000,'timeline':'6-18 months','platforms_focus':['youtube','tiktok','instagram'],'content_strategy':'video-first with distribution loops','growth_tactics':['creator network','format expansion'],'budget_estimate':35000,'key_metrics':['watch_time','shares','conversion_rate']},{'name':'Dominance','target':100000000,'timeline':'18-48 months','platforms_focus':['all'],'content_strategy':'multi-language multi-format franchise','growth_tactics':['localization','media partnerships'],'budget_estimate':250000,'key_metrics':['global reach','brand search volume']}]}
