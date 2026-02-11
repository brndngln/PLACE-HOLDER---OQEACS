from __future__ import annotations

import asyncio

from src.main import health, metrics
from src.service import OmniService


def test_health():
    payload = asyncio.run(health())
    assert payload["status"] == "healthy"


def test_metrics():
    response = asyncio.run(metrics())
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")


def test_primary_endpoint_logic():
    service = asyncio.run(OmniService.create("test-rca-synth"))
    payload = asyncio.run(service.handle("rca_analyze_post", {"example": "value"}, {}))
    asyncio.run(service.shutdown())
    assert isinstance(payload.get("ok"), bool)
    assert "operation" in payload
