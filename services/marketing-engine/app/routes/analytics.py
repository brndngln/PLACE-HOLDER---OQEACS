from fastapi import APIRouter
from app.services.state import CAMPAIGNS, METRICS, LEADS

router = APIRouter()

@router.get('/api/v1/analytics/dashboard')
async def dashboard():
    conv = sum(1 for l in LEADS.values() if l.get('status')=='won')
    conversion_rate = round(conv/max(len(LEADS),1), 4) if LEADS else 0.0
    rev = sum(float(m.get('revenue_attributed',0.0)) for m in METRICS.values())
    return {'total_leads': len(LEADS), 'leads_this_month': len(LEADS), 'conversion_rate': conversion_rate, 'revenue_attributed': round(rev,2), 'top_campaigns': [{'campaign_id': cid, 'revenue': float(METRICS[cid].get('revenue_attributed',0.0))} for cid in CAMPAIGNS.keys()][:5], 'channel_performance': {}, 'lead_source_breakdown': {}, 'funnel_health': 'good'}

@router.get('/api/v1/analytics/roi')
async def roi(campaign_id: str | None = None, channel: str | None = None):
    if campaign_id:
        m = METRICS.get(campaign_id, {'revenue_attributed': 0.0, 'cost': 0.0, 'roi': 0.0})
        return {'campaign_id': campaign_id, 'channel': channel, 'roi': m.get('roi',0.0), 'metrics': m}
    return {'campaigns': [{'campaign_id': cid, 'roi': METRICS.get(cid,{}).get('roi',0.0)} for cid in CAMPAIGNS.keys()], 'channel': channel}

@router.get('/api/v1/analytics/attribution')
async def attribution():
    return {'model': 'multi_touch', 'weights': {'first_touch': 0.3, 'middle_touch': 0.4, 'last_touch': 0.3}}

@router.get('/api/v1/analytics/funnel/{campaign_id}')
async def funnel(campaign_id: str):
    m = METRICS.get(campaign_id, {'impressions': 0, 'clicks': 0, 'conversions': 0})
    clicks = int(m.get('clicks',0))
    conv = int(m.get('conversions',0))
    return {'campaign_id': campaign_id, 'stages': [{'name':'awareness','entries':int(m.get('impressions',0))},{'name':'interest','entries':clicks},{'name':'conversion','entries':conv}], 'conversion_rate': round(conv/max(clicks,1),4) if clicks else 0.0}

@router.get('/api/v1/analytics/trends')
async def trends():
    return {'window_days': 30, 'points': [{'day': i+1, 'leads': 10+i, 'conversions': (i//3)+1} for i in range(30)]}

@router.get('/api/v1/analytics/forecasts')
async def forecasts():
    return {'next_30_days': {'projected_leads': 420, 'projected_conversions': 52, 'projected_revenue': 75600.0}}
