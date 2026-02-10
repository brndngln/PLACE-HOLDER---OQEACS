"""Chatwoot SDK client."""
from __future__ import annotations
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class ChatwootClient:
    """Typed API client for Chatwoot."""

    def __init__(self, base_url: str, api_token: str):
        self._client = httpx.Client(base_url=base_url, headers={"api_access_token": api_token}, timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params); r.raise_for_status(); return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post(path, json=data); r.raise_for_status(); return r.json()

    def list_conversations(self, status: str | None = None) -> list[dict[str, Any]]:
        data = self._get("/api/v1/accounts/1/conversations", status=status) if status else self._get("/api/v1/accounts/1/conversations")
        return data.get("data", [])

    def get_conversation(self, conversation_id: int) -> dict[str, Any]:
        return self._get(f"/api/v1/accounts/1/conversations/{conversation_id}")

    def send_message(self, conversation_id: int, content: str) -> dict[str, Any]:
        logger.info("chatwoot_send_message", conversation_id=conversation_id)
        return self._post(f"/api/v1/accounts/1/conversations/{conversation_id}/messages", {"content": content, "message_type": "outgoing"})

    def assign_agent(self, conversation_id: int, agent_id: int) -> dict[str, Any]:
        return self._post(f"/api/v1/accounts/1/conversations/{conversation_id}/assignments", {"assignee_id": agent_id})

    def add_label(self, conversation_id: int, label: str) -> dict[str, Any]:
        return self._post(f"/api/v1/accounts/1/conversations/{conversation_id}/labels", {"labels": [label]})

    def create_contact(self, email: str, name: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"email": email, "name": name, **kwargs}
        return self._post("/api/v1/accounts/1/contacts", payload)

    def search_contacts(self, query: str) -> list[dict[str, Any]]:
        return self._get("/api/v1/accounts/1/contacts/search", q=query).get("payload", [])
