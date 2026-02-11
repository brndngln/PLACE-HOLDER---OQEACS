from __future__ import annotations
from typing import Any

import httpx

class MarketingEngineClient:
    def __init__(self, base_url: str = "http://localhost:9640", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "MarketingEngineClient":
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._client is None:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                resp = await client.request(method, path, **kwargs)
        else:
            resp = await self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.text

    async def create_campaign(self, name: str, campaign_type: str, channels: list[str], description: str = "") -> dict:
        return await self._request("POST", "/api/v1/campaigns", json={"name": name, "campaign_type": campaign_type, "channels": channels, "description": description})

    async def list_campaigns(self, status: str | None = None, type: str | None = None) -> list:
        params = {"status": status, "type": type}
        params = {k: v for k, v in params.items() if v is not None}
        return await self._request("GET", "/api/v1/campaigns", params=params)

    async def launch_campaign(self, campaign_id: str) -> dict:
        return await self._request("POST", f"/api/v1/campaigns/{campaign_id}/launch")

    async def get_campaign_metrics(self, campaign_id: str) -> dict:
        return await self._request("GET", f"/api/v1/campaigns/{campaign_id}/metrics")

    async def generate_ad_copy(self, product: str, audience: str, tone: str, variants: int = 5) -> dict:
        return await self._request("POST", "/api/v1/content/generate/ad-copy", json={"product_description": product, "target_audience": audience, "tone": tone, "channel": "email", "variant_count": variants})

    async def generate_email(self, purpose: str, audience: str, product: str) -> dict:
        return await self._request("POST", "/api/v1/content/generate/email", json={"purpose": purpose, "audience": audience, "product": product})

    async def generate_landing_page(self, product: str, value_prop: str, audience: str) -> dict:
        return await self._request("POST", "/api/v1/content/generate/landing-page", json={"product": product, "value_proposition": value_prop, "target_audience": audience})

    async def generate_lead_magnet(self, topic: str, format: str, audience: str) -> dict:
        return await self._request("POST", "/api/v1/content/generate/lead-magnet", json={"topic": topic, "format": format, "audience": audience})

    async def generate_seo_article(self, keyword: str, audience: str, length: int = 1200) -> dict:
        return await self._request("POST", "/api/v1/content/generate/seo-article", json={"primary_keyword": keyword, "target_length": length, "audience": audience})

    async def generate_content_calendar(self, goals: list[str], channels: list[str], days: int) -> dict:
        return await self._request("POST", "/api/v1/calendar/generate", json={"goals": goals, "channels": channels, "days": days})

    async def capture_lead(self, email: str, source: str, **kwargs: Any) -> dict:
        payload = {"email": email, "source": source, **kwargs}
        return await self._request("POST", "/api/v1/leads", json=payload)

    async def get_lead(self, lead_id: str) -> dict:
        return await self._request("GET", f"/api/v1/leads/{lead_id}")

    async def update_lead_score(self, lead_id: str) -> dict:
        return await self._request("POST", f"/api/v1/leads/{lead_id}/score")

    async def record_activity(self, lead_id: str, activity_type: str, metadata: dict) -> dict:
        return await self._request("POST", f"/api/v1/leads/{lead_id}/activity", json={"activity_type": activity_type, "metadata": metadata})

    async def create_ab_test(self, campaign_id: str, variants: list[dict]) -> dict:
        return await self._request("POST", f"/api/v1/ab-tests/{campaign_id}/create", json={"variants": variants})

    async def get_ab_results(self, campaign_id: str) -> dict:
        return await self._request("GET", f"/api/v1/ab-tests/{campaign_id}/results")

    async def declare_winner(self, campaign_id: str, variant_id: str) -> dict:
        return await self._request("POST", f"/api/v1/ab-tests/{campaign_id}/declare-winner", json={"variant_id": variant_id})

    async def get_dashboard(self) -> dict:
        return await self._request("GET", "/api/v1/analytics/dashboard")

    async def get_roi(self, campaign_id: str | None = None, channel: str | None = None) -> dict:
        return await self._request("GET", "/api/v1/analytics/roi", params={"campaign_id": campaign_id, "channel": channel})

    async def get_funnel(self, campaign_id: str) -> dict:
        return await self._request("GET", f"/api/v1/analytics/funnel/{campaign_id}")

    async def add_competitor(self, name: str, website: str | None = None) -> dict:
        return await self._request("POST", "/api/v1/competitors", json={"name": name, "website": website})

    async def analyze_competitor(self, competitor_id: str) -> dict:
        return await self._request("POST", f"/api/v1/competitors/{competitor_id}/analyze")

    async def get_comparison(self) -> dict:
        return await self._request("GET", "/api/v1/competitors/comparison")

    async def identify_gaps(self, our_features: list[str], our_pricing: str) -> dict:
        return await self._request("POST", "/api/v1/competitors/gaps", json={"our_features": our_features, "our_pricing": our_pricing})
