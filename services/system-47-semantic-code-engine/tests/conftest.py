from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def async_client() -> AsyncClient:
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    (tmp_path / "main.py").write_text(
        "from utils import helper\\n\\ndef calc(x:int)->int:\\n    return helper(x)+1\\n",
        encoding="utf-8",
    )
    (tmp_path / "utils.py").write_text(
        "def helper(v:int)->int:\\n    return v*2\\n",
        encoding="utf-8",
    )
    (tmp_path / "test_main.py").write_text(
        "from main import calc\\n\\ndef test_calc():\\n    assert calc(2)==5\\n",
        encoding="utf-8",
    )
    return tmp_path
