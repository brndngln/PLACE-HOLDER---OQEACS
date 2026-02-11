from fastapi import APIRouter, HTTPException, Query
from app.models.requests import CreateLeadRequest, RecordActivityRequest
from app.services.state import LEADS, LEAD_ACTIVITIES, now, uid

router = APIRouter()

def compute_score(lead: dict, acts: list[dict]) -> tuple[int, dict]:
    score = 0
    breakdown = {}
    def add(k, d):
        nonlocal score
        score += d
        breakdown[k] = breakdown.get(k, 0) + d
    for a in acts:
        t = a.get("activity_type")
        if t == "page_visit" and "pricing" in str(a.get("metadata", {}).get("page_url", "")):
            add("pricing", 20)
        if t == "download":
            add("download", 15)
        if t == "email_click":
            add("email_click", 10)
        if t in {"form_submit", "demo_request"}:
            add("high_intent", 25)
        if t == "unsubscribe":
            add("unsubscribe", -10)
        if t == "email_bounce":
            add("bounce", -20)
    if int(lead.get("company_size") or 0) > 50:
        add("company_size", 15)
    title = str(lead.get("job_title", "")).lower()
    if any(x in title for x in ["ceo", "cto", "vp", "director", "head"]):
        add("title", 10)
    if str(lead.get("industry", "")).lower() in {"tech", "software", "ai", "saas"}:
        add("industry", 5)
    if lead["email"].split("@")[-1].lower() in {"gmail.com", "yahoo.com"}:
        add("generic", -5)
    score = max(0, min(100, score))
    return score, breakdown

def band(score: int) -> str:
    if score <= 25:
        return "Cold"
    if score <= 50:
        return "Warm"
    if score <= 75:
        return "Hot"
    return "Sales-Ready"

@router.post("/api/v1/leads", status_code=201)
async def capture_lead(payload: CreateLeadRequest):
    lead_id = uid()
    lead = payload.model_dump()
    lead.update({"id": lead_id, "status": "new", "created_at": now(), "updated_at": now(), "last_activity_at": now()})
    LEADS[lead_id] = lead
    LEAD_ACTIVITIES[lead_id] = []
    score, breakdown = compute_score(lead, LEAD_ACTIVITIES[lead_id])
    lead["score"] = score
    lead["score_breakdown"] = breakdown
    return lead

@router.post("/api/v1/leads/bulk")
async def bulk_import(payload: dict):
    items = []
    for row in payload.get("leads", []):
        items.append((await capture_lead(CreateLeadRequest(**row))))
    return {"created": len(items), "items": items}

@router.get("/api/v1/leads")
async def list_leads(status: str | None = Query(default=None), score_min: int | None = Query(default=None), source: str | None = Query(default=None), sort: str | None = Query(default=None)):
    rows = list(LEADS.values())
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if score_min is not None:
        rows = [r for r in rows if int(r.get("score", 0)) >= score_min]
    if source:
        rows = [r for r in rows if r.get("source") == source]
    if sort == "score_desc":
        rows.sort(key=lambda x: int(x.get("score", 0)), reverse=True)
    return rows

@router.get("/api/v1/leads/{lead_id}")
async def get_lead(lead_id: str):
    lead = LEADS.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    out = dict(lead)
    out["activities"] = LEAD_ACTIVITIES.get(lead_id, [])
    return out

@router.put("/api/v1/leads/{lead_id}")
async def update_lead(lead_id: str, payload: dict):
    lead = LEADS.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    lead.update(payload)
    lead["updated_at"] = now()
    return lead

@router.delete("/api/v1/leads/{lead_id}")
async def delete_lead(lead_id: str):
    if lead_id not in LEADS:
        raise HTTPException(status_code=404, detail="lead not found")
    LEADS.pop(lead_id, None)
    LEAD_ACTIVITIES.pop(lead_id, None)
    return {"deleted": True}

@router.post("/api/v1/leads/{lead_id}/score")
async def rescore(lead_id: str):
    lead = LEADS.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    score, breakdown = compute_score(lead, LEAD_ACTIVITIES.get(lead_id, []))
    lead["score"] = score
    lead["score_breakdown"] = breakdown
    return {"lead_id": lead_id, "score": score, "breakdown": breakdown, "label": band(score)}

@router.post("/api/v1/leads/{lead_id}/activity")
async def record_activity(lead_id: str, payload: RecordActivityRequest):
    if lead_id not in LEADS:
        raise HTTPException(status_code=404, detail="lead not found")
    row = {"id": uid(), "activity_type": payload.activity_type, "metadata": payload.metadata, "created_at": now()}
    LEAD_ACTIVITIES.setdefault(lead_id, []).append(row)
    LEADS[lead_id]["last_activity_at"] = row["created_at"]
    await rescore(lead_id)
    return row

@router.get("/api/v1/leads/{lead_id}/activities")
async def activities(lead_id: str):
    if lead_id not in LEADS:
        raise HTTPException(status_code=404, detail="lead not found")
    return {"lead_id": lead_id, "activities": LEAD_ACTIVITIES.get(lead_id, [])}

@router.post("/api/v1/leads/{lead_id}/nurture")
async def nurture(lead_id: str, payload: dict | None = None):
    payload = payload or {}
    if lead_id not in LEADS:
        raise HTTPException(status_code=404, detail="lead not found")
    LEADS[lead_id]["status"] = "nurturing"
    LEADS[lead_id]["nurture_sequence_id"] = payload.get("sequence_id")
    return LEADS[lead_id]

@router.post("/api/v1/leads/{lead_id}/convert")
async def convert(lead_id: str, payload: dict | None = None):
    payload = payload or {}
    if lead_id not in LEADS:
        raise HTTPException(status_code=404, detail="lead not found")
    LEADS[lead_id]["status"] = "won"
    LEADS[lead_id]["revenue_value"] = payload.get("revenue_value")
    return LEADS[lead_id]

@router.get("/api/v1/leads/scoring-model")
async def scoring_model():
    return {"rules": [{"activity": "pricing_page", "score_delta": 20}, {"activity": "download", "score_delta": 15}, {"activity": "email_click", "score_delta": 10}]}

@router.put("/api/v1/leads/scoring-model")
async def scoring_model_update(payload: dict):
    return {"updated": True, "rules": payload.get("rules", [])}
