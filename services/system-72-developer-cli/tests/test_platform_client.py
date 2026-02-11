from __future__ import annotations

import pytest

from src.services.platform_client import PlatformClient


@pytest.mark.anyio
async def test_get_status_shape() -> None:
    status = await PlatformClient().get_status()
    assert status.total_services >= 1


@pytest.mark.anyio
async def test_services_list() -> None:
    status = await PlatformClient().get_status()
    assert isinstance(status.services, list)


@pytest.mark.anyio
async def test_counts_consistent() -> None:
    status = await PlatformClient().get_status()
    assert status.total_services == status.healthy_services + status.unhealthy_services
