from datetime import date, timedelta
from fastapi import APIRouter
from app.routes.accounts import ACCOUNTS
from app.routes.publishing import POSTS

router = APIRouter()
MILESTONES = []

@router.get('/api/v1/analytics/dashboard')
async def dashboard():
    by = {}
    for a in ACCOUNTS.values():
        by[a['platform']] = by.get(a['platform'],0) + int(a.get('follower_count',0))
    total = sum(by.values())
    published = [p for p in POSTS.values() if p['status']=='published']
    top = sorted(published, key=lambda x: x.get('engagement_rate',0.0), reverse=True)[:5]
    rec = ['Increase LinkedIn cadence to 2/day', 'Publish trend responses within 60 minutes']
    return {'total_followers': total, 'followers_by_platform': by, 'total_engagement_this_week': sum(int(p.get('likes',0))+int(p.get('comments',0))+int(p.get('shares',0)) for p in published), 'top_performing_posts': top, 'growth_rate': 0.12, 'content_pillar_performance': {}, 'best_performing_platform': max(by, key=by.get) if by else None, 'worst_performing_platform': min(by, key=by.get) if by else None, 'recommended_actions': rec, 'next_milestones': MILESTONES[-3:]}

@router.get('/api/v1/analytics/growth')
async def growth(platform: str | None = None, range: str = '30d'):
    days = int(range.rstrip('d')) if range.endswith('d') else 30
    points = [{'date': (date.today()-timedelta(days=days-i)).isoformat(), 'followers': i*100} for i in range(days)]
    return {'platform': platform, 'window_days': days, 'snapshots': points}

@router.get('/api/v1/analytics/growth/projection')
async def projection():
    total = sum(int(a.get('follower_count',0)) for a in ACCOUNTS.values())
    return {'current_total': total, 'monthly_growth_rate': 0.18, 'projected_milestones': [{'count': 1000000, 'estimated_date': (date.today()+timedelta(days=90)).isoformat()}, {'count': 10000000, 'estimated_date': (date.today()+timedelta(days=365)).isoformat()}, {'count': 100000000, 'estimated_date': (date.today()+timedelta(days=1200)).isoformat()}], 'bottlenecks': ['posting consistency','platform diversification'], 'acceleration_recommendations': ['increase collaborations','double down on best pillar']}

@router.get('/api/v1/analytics/posts/performance')
async def perf():
    rows = list(POSTS.values())
    rows.sort(key=lambda x: x.get('engagement_rate',0.0), reverse=True)
    return rows

@router.get('/api/v1/analytics/posts/best-times')
async def best_times():
    return {'twitter': ['09:00','13:00','18:00'], 'linkedin': ['08:30','12:00','17:00']}

@router.get('/api/v1/analytics/posts/best-formats')
async def best_formats():
    return {'formats': [{'format':'thread','engagement':0.061},{'format':'carousel','engagement':0.055}]}

@router.get('/api/v1/analytics/posts/best-pillars')
async def best_pillars():
    return {'pillars': [{'name':'educational','engagement':0.058},{'name':'inspiring','engagement':0.051}]}

@router.get('/api/v1/analytics/posts/viral')
async def viral():
    return [p for p in POSTS.values() if float(p.get('engagement_rate',0.0)) > 0.05]

@router.get('/api/v1/analytics/engagement-rate')
async def engagement_rate():
    if not POSTS:
        return {'engagement_rate': 0.0}
    avg = sum(float(p.get('engagement_rate',0.0)) for p in POSTS.values())/len(POSTS)
    return {'engagement_rate': round(avg,4)}

@router.get('/api/v1/analytics/milestones')
async def milestones():
    return MILESTONES

@router.get('/api/v1/analytics/report')
async def report(period: str = 'weekly'):
    board = await dashboard()
    return {'period': period, 'report_markdown': f"# Social Report ({period})\nTotal followers: {board['total_followers']}\n", 'executive_summary': 'Growth is positive with strong trend responsiveness.', 'key_metrics': board, 'recommendations': board['recommended_actions']}
