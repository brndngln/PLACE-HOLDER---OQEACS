from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx


class FormbricksClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    def list_surveys(self) -> list[dict[str, Any]]:
        resp = self.client.get("/api/v1/surveys")
        resp.raise_for_status()
        return resp.json().get("data", [])

    def create_survey(self, template: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        payload = {**template, **kwargs}
        resp = self.client.post("/api/v1/surveys", json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_responses(self, survey_id: str, since: datetime | None = None) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if since:
            params["since"] = since.isoformat()
        resp = self.client.get(f"/api/v1/surveys/{survey_id}/responses", params=params)
        resp.raise_for_status()
        return resp.json().get("data", [])

    def get_survey_analytics(self, survey_id: str) -> dict[str, Any]:
        resp = self.client.get(f"/api/v1/surveys/{survey_id}/analytics")
        resp.raise_for_status()
        return resp.json()

    def create_response_webhook(self, survey_id: str, webhook_url: str) -> dict[str, Any]:
        resp = self.client.post(
            f"/api/v1/surveys/{survey_id}/webhooks",
            json={"url": webhook_url, "events": ["response.created"]},
        )
        resp.raise_for_status()
        return resp.json()
