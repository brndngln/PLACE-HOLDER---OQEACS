import asyncio

import httpx
import pytest

from app.main import app
from app.services import state


class SyncASGIClient:
    def __init__(self, app_instance) -> None:
        self._app = app_instance

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        async def runner() -> httpx.Response:
            transport = httpx.ASGITransport(app=self._app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(runner())

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> httpx.Response:
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> httpx.Response:
        return self._request("DELETE", path, **kwargs)


@pytest.fixture(autouse=True)
def reset_state():
    state.CAMPAIGNS.clear()
    state.METRICS.clear()
    state.LEADS.clear()
    state.LEAD_ACTIVITIES.clear()
    state.AUDIENCES.clear()
    state.SEQUENCES.clear()
    state.LANDING_PAGES.clear()
    state.CALENDAR.clear()
    state.COMPETITORS.clear()
    state.COMPETITOR_SNAPSHOTS.clear()
    state.AB_TESTS.clear()


@pytest.fixture()
def client() -> SyncASGIClient:
    return SyncASGIClient(app)
