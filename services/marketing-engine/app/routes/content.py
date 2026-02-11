from fastapi import APIRouter
from app.models.requests import GenerateAdCopyRequest

router = APIRouter()

@router.post("/api/v1/content/generate/ad-copy")
async def generate_ad_copy(payload: GenerateAdCopyRequest):
    variants = []
    for idx in range(payload.variant_count):
        variants.append({"headline": f"{payload.target_audience} - {payload.product_description} ({idx+1})", "body": f"Tone={payload.tone} Channel={payload.channel}", "cta": "Start now", "hook": "Limited spots", "emotional_angle": "confidence"})
    return {"variants": variants}

@router.post("/api/v1/content/generate/email")
async def generate_email(payload: dict):
    return {"subject_lines": ["Subject A", "Subject B", "Subject C", "Subject D", "Subject E"], "preview_text": "Preview", "body_html": "<html><body><h1>Email</h1></body></html>", "body_plain": "Email", "cta": "Reply"}

@router.post("/api/v1/content/generate/landing-page")
async def generate_landing_page(payload: dict):
    html = "<!doctype html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'></head><body><main><form><button>CTA</button></form></main></body></html>"
    return {"html": html, "title": payload.get("product", "Landing"), "meta_description": payload.get("value_proposition", ""), "og_tags": {"og:title": payload.get("product", "Landing")}}

@router.post("/api/v1/content/generate/lead-magnet")
async def generate_lead_magnet(payload: dict):
    return {"content_markdown": "# Lead Magnet\\n\\nDetails", "title": payload.get("topic", "Guide"), "cover_image_brief": "Cover brief", "download_url": "minio://marketing-lead-magnets/file.md"}

@router.post("/api/v1/content/generate/seo-article")
async def generate_seo_article(payload: dict):
    keyword = payload.get("primary_keyword", "keyword")
    body = (keyword + " ") * 120
    return {"title": f"{keyword} guide", "meta_description": keyword, "article_html": f"<article>{body}</article>", "word_count": len(body.split()), "readability_score": 0.82, "keyword_density": 0.1}

@router.post("/api/v1/content/improve")
async def improve_content(payload: dict):
    goals = payload.get("improvement_goals", payload.get("goals", []))
    improved = payload.get("content", "")
    if "more_engaging" in goals:
        improved = "Hook: " + improved
    return {"improved_content": improved, "changes_made": goals, "improvement_score": 0.9}
