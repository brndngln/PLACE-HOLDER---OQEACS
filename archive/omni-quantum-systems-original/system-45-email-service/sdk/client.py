"""Listmonk SDK client."""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from pydantic import BaseModel, EmailStr
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class CampaignStats(BaseModel):
    id: int
    name: str
    sent: int = 0
    opens: int = 0
    clicks: int = 0


class ListmonkClient:
    """Typed Listmonk API client."""

    def __init__(self, base_url: str, api_credentials: str):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Basic {api_credentials}"},
            timeout=30.0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.post(path, json=data)
        resp.raise_for_status()
        return resp.json()

    def send_transactional(self, template_name: str, to_email: str, merge_data: dict[str, Any]) -> dict[str, Any]:
        logger.info("sending_transactional_email", template=template_name, recipient=to_email)
        return self._post(
            "/api/tx",
            {"template": template_name, "subscriber_email": to_email, "data": merge_data},
        )

    def create_subscriber(self, email: str, name: str, lists: list[int]) -> dict[str, Any]:
        payload = {"email": EmailStr(email), "name": name, "lists": lists, "status": "enabled"}
        return self._post("/api/subscribers", payload)

    def list_campaigns(self) -> list[dict[str, Any]]:
        return self._get("/api/campaigns").get("data", [])

    def get_campaign_stats(self, campaign_id: int) -> CampaignStats:
        data = self._get(f"/api/campaigns/{campaign_id}/stats").get("data", {})
        return CampaignStats(**data)
