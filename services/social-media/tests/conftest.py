import asyncio

import httpx
import pytest

from app.main import app
from app.routes import accounts, competitors, engagement, publishing, trends


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
    accounts.ACCOUNTS.clear()
    publishing.POSTS.clear()
    trends.TRENDS.clear()
    competitors.COMPETITORS.clear()
    competitors.COMP_POSTS.clear()
    engagement.QUEUE.clear()


@pytest.fixture()
def client() -> SyncASGIClient:
    return SyncASGIClient(app)
