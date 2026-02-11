from __future__ import annotations
from typing import Any

import httpx

class SocialMediaClient:
    def __init__(self, base_url: str = "http://localhost:9641", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "SocialMediaClient":
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

    async def connect_account(self, platform: str, handle: str, credentials: dict) -> dict:
        return await self._request("POST", "/api/v1/accounts", json={"platform": platform, "account_handle": handle, "credentials": credentials})

    async def list_accounts(self) -> list:
        return await self._request("GET", "/api/v1/accounts")

    async def get_overview(self) -> dict:
        return await self._request("GET", "/api/v1/accounts/overview")

    async def generate_content(self, topic: str, platforms: list[str], pillar: str, tone: str) -> dict:
        return await self._request("POST", "/api/v1/content/generate", json={"topic": topic, "platforms": platforms, "content_pillar": pillar, "tone": tone, "include_hashtags": True})

    async def repurpose(self, post_id: str, target_platforms: list[str]) -> dict:
        return await self._request("POST", "/api/v1/content/repurpose", json={"source_post_id": post_id, "target_platforms": target_platforms})

    async def research_hashtags(self, topic: str, platform: str, count: int) -> dict:
        return await self._request("POST", "/api/v1/content/hashtag-research", json={"topic": topic, "platform": platform, "count": count})

    async def create_post(self, text: str, platform: str, account_id: str, media_urls: list[str] | None = None, format: str | None = None) -> dict:
        return await self._request("POST", "/api/v1/posts", json={"text": text, "platform": platform, "account_id": account_id, "media_urls": media_urls or [], "format": format or "text"})

    async def schedule_post(self, post_id: str, scheduled_at: str) -> dict:
        return await self._request("POST", f"/api/v1/posts/{post_id}/schedule", json={"scheduled_at": scheduled_at})

    async def publish_now(self, post_id: str) -> dict:
        return await self._request("POST", f"/api/v1/posts/{post_id}/publish")

    async def cross_post(self, text: str, platforms: list[str], adapt: bool = True) -> dict:
        return await self._request("POST", "/api/v1/posts/cross-post", json={"text": text, "platforms": platforms, "adapt_per_platform": adapt})

    async def bulk_schedule(self, posts: list[dict]) -> dict:
        return await self._request("POST", "/api/v1/posts/bulk-schedule", json={"posts": posts})

    async def get_trends(self, platform: str | None = None, category: str | None = None) -> list:
        return await self._request("GET", "/api/v1/trends", params={"platform": platform, "category": category})

    async def create_post_from_trend(self, trend_id: str, platforms: list[str]) -> dict:
        return await self._request("POST", f"/api/v1/trends/{trend_id}/create-post", json={"platforms": platforms})

    async def add_competitor(self, platform: str, handle: str) -> dict:
        return await self._request("POST", "/api/v1/competitors", json={"platform": platform, "handle": handle})

    async def analyze_competitor(self, competitor_id: str) -> dict:
        return await self._request("POST", f"/api/v1/competitors/{competitor_id}/analyze")

    async def get_content_gaps(self) -> dict:
        return await self._request("GET", "/api/v1/competitors/content-gaps")

    async def get_dashboard(self) -> dict:
        return await self._request("GET", "/api/v1/analytics/dashboard")

    async def get_growth(self, platform: str | None = None, range: str = "30d") -> dict:
        return await self._request("GET", "/api/v1/analytics/growth", params={"platform": platform, "range": range})

    async def get_growth_projection(self) -> dict:
        return await self._request("GET", "/api/v1/analytics/growth/projection")

    async def get_viral_posts(self) -> list:
        return await self._request("GET", "/api/v1/analytics/posts/viral")

    async def get_milestones(self) -> list:
        return await self._request("GET", "/api/v1/analytics/milestones")

    async def get_recommendations(self) -> dict:
        return await self._request("GET", "/api/v1/strategy/recommendations")

    async def run_audit(self) -> dict:
        return await self._request("POST", "/api/v1/strategy/audit")

    async def get_100m_plan(self) -> dict:
        return await self._request("POST", "/api/v1/strategy/100m-plan")
