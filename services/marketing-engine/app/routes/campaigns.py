from fastapi import APIRouter, HTTPException, Query
from app.models.requests import CreateCampaignRequest
from app.services.state import CAMPAIGNS, METRICS, now, uid

router = APIRouter()

@router.post("/api/v1/campaigns", status_code=201)
async def create_campaign(payload: CreateCampaignRequest):
    campaign_id = uid()
    record = {"id": campaign_id, "name": payload.name, "campaign_type": payload.campaign_type, "channels": payload.channels, "description": payload.description, "status": "draft", "created_at": now(), "updated_at": now()}
    CAMPAIGNS[campaign_id] = record
    METRICS[campaign_id] = {"impressions": 0, "clicks": 0, "conversions": 0, "revenue_attributed": 0.0, "cost": 0.0, "roi": 0.0}
    return record

@router.get("/api/v1/campaigns")
async def list_campaigns(status: str | None = Query(default=None), type: str | None = Query(default=None), channel: str | None = Query(default=None)):
    rows = list(CAMPAIGNS.values())
    if status:
        rows = [r for r in rows if r["status"] == status]
    if type:
        rows = [r for r in rows if r["campaign_type"] == type]
    if channel:
        rows = [r for r in rows if channel in r.get("channels", [])]
    return rows

@router.get("/api/v1/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    if campaign_id not in CAMPAIGNS:
        raise HTTPException(status_code=404, detail="campaign not found")
    out = dict(CAMPAIGNS[campaign_id])
    out["metrics"] = METRICS.get(campaign_id, {})
    return out

@router.put("/api/v1/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, payload: dict):
    if campaign_id not in CAMPAIGNS:
        raise HTTPException(status_code=404, detail="campaign not found")
    CAMPAIGNS[campaign_id].update(payload)
    CAMPAIGNS[campaign_id]["updated_at"] = now()
    return CAMPAIGNS[campaign_id]

@router.delete("/api/v1/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str):
    campaign = CAMPAIGNS.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="campaign not found")
    if campaign["status"] != "draft":
        raise HTTPException(status_code=409, detail="only draft can be deleted")
    CAMPAIGNS.pop(campaign_id, None)
    METRICS.pop(campaign_id, None)
    return {"deleted": True}

def _status(campaign_id: str, value: str):
    if campaign_id not in CAMPAIGNS:
        raise HTTPException(status_code=404, detail="campaign not found")
    CAMPAIGNS[campaign_id]["status"] = value
    CAMPAIGNS[campaign_id]["updated_at"] = now()
    return CAMPAIGNS[campaign_id]

@router.post("/api/v1/campaigns/{campaign_id}/launch")
async def launch_campaign(campaign_id: str):
    return _status(campaign_id, "active")

@router.post("/api/v1/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    return _status(campaign_id, "paused")

@router.post("/api/v1/campaigns/{campaign_id}/resume")
async def resume_campaign(campaign_id: str):
    return _status(campaign_id, "active")

@router.post("/api/v1/campaigns/{campaign_id}/complete")
async def complete_campaign(campaign_id: str):
    return _status(campaign_id, "completed")

@router.get("/api/v1/campaigns/{campaign_id}/metrics")
async def campaign_metrics(campaign_id: str):
    if campaign_id not in CAMPAIGNS:
        raise HTTPException(status_code=404, detail="campaign not found")
    m = METRICS.get(campaign_id, {"impressions": 0, "clicks": 0, "conversions": 0, "revenue_attributed": 0.0, "cost": 0.0})
    impressions = int(m.get("impressions", 0))
    clicks = int(m.get("clicks", 0))
    conversions = int(m.get("conversions", 0))
    m["click_rate"] = round(clicks / impressions, 4) if impressions else 0.0
    m["conversion_rate"] = round(conversions / clicks, 4) if clicks else 0.0
    m["roi"] = round((float(m.get("revenue_attributed", 0.0)) - float(m.get("cost", 0.0))) / float(m.get("cost", 1.0)), 4) if float(m.get("cost", 0.0)) else 0.0
    METRICS[campaign_id] = m
    return m

@router.get("/api/v1/campaigns/{campaign_id}/funnel")
async def campaign_funnel(campaign_id: str):
    m = await campaign_metrics(campaign_id)
    return {"campaign_id": campaign_id, "stages": [{"name": "awareness", "entries": m["impressions"]}, {"name": "interest", "entries": m["clicks"]}, {"name": "conversion", "entries": m["conversions"]}], "conversion_rate": m["conversion_rate"]}

@router.post("/api/v1/campaigns/{campaign_id}/duplicate", status_code=201)
async def duplicate_campaign(campaign_id: str):
    if campaign_id not in CAMPAIGNS:
        raise HTTPException(status_code=404, detail="campaign not found")
    src = dict(CAMPAIGNS[campaign_id])
    src["name"] = f"Copy of {src['name']}"
    src["status"] = "draft"
    src.pop("id", None)
    return await create_campaign(CreateCampaignRequest(**{k: src.get(k) for k in ["name", "campaign_type", "channels", "description"]}))
