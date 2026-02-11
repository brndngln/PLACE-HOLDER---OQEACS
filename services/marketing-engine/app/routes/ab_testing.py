from fastapi import APIRouter, HTTPException
from app.services.state import AB_TESTS, uid

router = APIRouter()

@router.post("/api/v1/ab-tests/{campaign_id}/create")
async def create_ab_test(campaign_id: str, payload: dict | None = None):
    payload = payload or {}
    variants = payload.get("variants", [{"label": "A", "traffic_weight": 0.5}, {"label": "B", "traffic_weight": 0.5}])
    AB_TESTS[campaign_id] = {"campaign_id": campaign_id, "variants": [{"id": uid(), "label": v.get("label", "A"), "traffic_weight": float(v.get("traffic_weight", 0.5)), "impressions": 0, "clicks": 0, "conversions": 0, "is_winner": False} for v in variants], "winner_variant_id": None}
    return AB_TESTS[campaign_id]

@router.post("/api/v1/ab-tests/{campaign_id}/record")
async def record_event(campaign_id: str, payload: dict):
    test = AB_TESTS.get(campaign_id)
    if not test:
        raise HTTPException(status_code=404, detail="test not found")
    for v in test["variants"]:
        if v["label"] == payload.get("variant_label", "A"):
            et = payload.get("event_type", "impressions")
            v[et] = int(v.get(et, 0)) + int(payload.get("value", 1))
            return v
    raise HTTPException(status_code=404, detail="variant not found")

@router.get("/api/v1/ab-tests/{campaign_id}/results")
async def results(campaign_id: str):
    test = AB_TESTS.get(campaign_id)
    if not test:
        raise HTTPException(status_code=404, detail="test not found")
    complete = False
    for v in test["variants"]:
        imp = max(v["impressions"], 1)
        clk = v["clicks"]
        conv = v["conversions"]
        v["click_rate"] = round(clk / imp, 4)
        v["conversion_rate"] = round(conv / max(clk, 1), 4)
        v["confidence_interval"] = [max(0.0, v["conversion_rate"] - 0.05), min(1.0, v["conversion_rate"] + 0.05)]
        if imp >= 100:
            complete = True
    return {"variants": test["variants"], "test_complete": complete, "recommended_action": "declare_winner" if complete else "keep_running", "statistical_significance": complete}

@router.post("/api/v1/ab-tests/{campaign_id}/declare-winner")
async def declare_winner(campaign_id: str, payload: dict | None = None):
    payload = payload or {}
    test = AB_TESTS.get(campaign_id)
    if not test:
        raise HTTPException(status_code=404, detail="test not found")
    winner = payload.get("variant_id") or max(test["variants"], key=lambda x: x.get("conversion_rate", 0.0))["id"]
    test["winner_variant_id"] = winner
    for v in test["variants"]:
        v["is_winner"] = v["id"] == winner
        v["traffic_weight"] = 1.0 if v["is_winner"] else 0.0
    return test
