import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

STAGE_PROBABILITY = {
    "Lead": 0.10,
    "Qualified": 0.25,
    "Proposal Sent": 0.50,
    "Negotiation": 0.75,
    "Active Project": 0.90,
    "Completed": 1.0,
    "Lost": 0.0,
}


class TwentyCRMClient:
    def __init__(
        self,
        base_url: str = "http://omni-twenty:3000/api",
        api_token: str = "",
    ):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=30.0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params) -> dict:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict) -> dict:
        r = self._client.post(path, json=data)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _patch(self, path: str, data: dict) -> dict:
        r = self._client.patch(path, json=data)
        r.raise_for_status()
        return r.json()

    def list_companies(self) -> list:
        return self._get("/companies").get("data", [])

    def create_company(self, **kw) -> dict:
        return self._post("/companies", kw)

    def list_contacts(self, company_id: str | None = None) -> list:
        params = {"company_id": company_id} if company_id else {}
        return self._get("/contacts", **params).get("data", [])

    def create_contact(self, **kw) -> dict:
        return self._post("/contacts", kw)

    def list_deals(self, stage: str | None = None) -> list:
        params = {"stage": stage} if stage else {}
        return self._get("/deals", **params).get("data", [])

    def create_deal(self, **kw) -> dict:
        return self._post("/deals", kw)

    def update_deal(self, deal_id: str, **kw) -> dict:
        return self._patch(f"/deals/{deal_id}", kw)

    def get_deal(self, deal_id: str) -> dict:
        return self._get(f"/deals/{deal_id}")

    def pipeline_summary(self) -> dict:
        deals = self.list_deals()
        summary = {}
        for deal in deals:
            stage = deal.get("stage", "Unknown")
            value = deal.get("total_value", 0) or 0
            if stage not in summary:
                summary[stage] = {"count": 0, "total_value": 0}
            summary[stage]["count"] += 1
            summary[stage]["total_value"] += value
        return summary

    def revenue_forecast(self) -> dict:
        deals = self.list_deals()
        total_weighted = 0
        by_stage = {}
        for deal in deals:
            stage = deal.get("stage", "Unknown")
            value = deal.get("total_value", 0) or 0
            prob = STAGE_PROBABILITY.get(stage, 0)
            weighted = value * prob
            total_weighted += weighted
            if stage not in by_stage:
                by_stage[stage] = {"count": 0, "value": 0, "weighted": 0, "probability": prob}
            by_stage[stage]["count"] += 1
            by_stage[stage]["value"] += value
            by_stage[stage]["weighted"] += weighted
        return {"by_stage": by_stage, "total_weighted": total_weighted}
