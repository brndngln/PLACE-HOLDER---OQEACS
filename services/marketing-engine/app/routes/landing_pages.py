from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from app.models.requests import CreateLandingPageRequest
from app.services.state import LANDING_PAGES, LEADS, uid, now

router = APIRouter()

@router.post('/api/v1/landing-pages', status_code=201)
async def create_page(payload: CreateLandingPageRequest):
    pid = uid()
    LANDING_PAGES[pid] = {'id': pid, 'campaign_id': payload.campaign_id, 'slug': payload.slug, 'title': payload.title, 'html_content': payload.html_content, 'status': 'draft', 'views': 0, 'submissions': 0, 'conversion_rate': 0.0, 'created_at': now(), 'redirect_url': payload.redirect_url}
    return LANDING_PAGES[pid]

@router.get('/api/v1/landing-pages')
async def list_pages():
    return list(LANDING_PAGES.values())

@router.get('/api/v1/landing-pages/{page_id}')
async def get_page(page_id: str):
    if page_id not in LANDING_PAGES:
        raise HTTPException(status_code=404, detail='page not found')
    return LANDING_PAGES[page_id]

@router.put('/api/v1/landing-pages/{page_id}')
async def update_page(page_id: str, payload: dict):
    if page_id not in LANDING_PAGES:
        raise HTTPException(status_code=404, detail='page not found')
    LANDING_PAGES[page_id].update(payload)
    return LANDING_PAGES[page_id]

@router.post('/api/v1/landing-pages/{page_id}/publish')
async def publish_page(page_id: str):
    if page_id not in LANDING_PAGES:
        raise HTTPException(status_code=404, detail='page not found')
    LANDING_PAGES[page_id]['status'] = 'published'
    LANDING_PAGES[page_id]['published_at'] = now()
    return LANDING_PAGES[page_id]

def _by_slug(slug: str):
    for page in LANDING_PAGES.values():
        if page['slug'] == slug and page['status'] == 'published':
            return page
    return None

@router.get('/p/{slug}')
async def render(slug: str):
    page = _by_slug(slug)
    if not page:
        raise HTTPException(status_code=404, detail='page not found')
    page['views'] += 1
    page['conversion_rate'] = round(page['submissions']/max(page['views'],1), 4)
    return HTMLResponse(page['html_content'])

@router.post('/p/{slug}/submit')
async def submit(slug: str, payload: dict):
    page = _by_slug(slug)
    if not page:
        raise HTTPException(status_code=404, detail='page not found')
    page['submissions'] += 1
    page['conversion_rate'] = round(page['submissions']/max(page['views'],1), 4)
    lead_id = uid()
    LEADS[lead_id] = {'id': lead_id, 'email': payload.get('email'), 'status': 'new', 'source': 'landing_page', 'created_at': now(), 'updated_at': now()}
    return {'lead': LEADS[lead_id], 'redirect_url': page.get('redirect_url')}

@router.get('/api/v1/landing-pages/{page_id}/metrics')
async def page_metrics(page_id: str):
    if page_id not in LANDING_PAGES:
        raise HTTPException(status_code=404, detail='page not found')
    page = LANDING_PAGES[page_id]
    return {'views': page['views'], 'submissions': page['submissions'], 'conversion_rate': page['conversion_rate']}
